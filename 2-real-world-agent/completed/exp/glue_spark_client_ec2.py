#!/usr/bin/env python3
"""
AWS Glue Interactive Sessions Client with EC2 Instance Profile Support
"""

import boto3
import time

class GlueSparkClient:
    def __init__(self, role_arn=None, region='us-west-2'):
        """
        Args:
            role_arn: Glue service role ARN. If None, will auto-detect from EC2 instance profile
            region: AWS region
        """
        self.glue = boto3.client('glue', region_name=region)
        self.sts = boto3.client('sts', region_name=region)
        self.session_id = None
        
        # Auto-detect role from EC2 instance profile if not provided
        if role_arn is None:
            self.role_arn = self._get_role_from_instance_profile()
        else:
            self.role_arn = role_arn
        
        print(f"🔑 Using role: {self.role_arn}")
    
    def _get_role_from_instance_profile(self):
        """EC2 인스턴스 프로파일에서 역할 ARN 가져오기"""
        try:
            # 현재 사용 중인 자격 증명 확인
            identity = self.sts.get_caller_identity()
            arn = identity['Arn']
            
            # assumed-role에서 역할 이름 추출
            if 'assumed-role' in arn:
                # arn:aws:sts::123456789012:assumed-role/MyRole/i-1234567890abcdef0
                role_name = arn.split('/')[-2]
                account_id = identity['Account']
                role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
                print(f"✅ Auto-detected role from EC2 instance profile: {role_name}")
                return role_arn
            else:
                raise Exception(
                    "Not running on EC2 with instance profile. "
                    "Please provide role_arn explicitly."
                )
        except Exception as e:
            raise Exception(f"Failed to get role from instance profile: {e}")
    
    def create_session(self, session_name='spark-session'):
        """Glue Interactive Session 생성"""
        print(f"🚀 Creating Glue session: {session_name}")
        
        response = self.glue.create_session(
            Id=session_name,
            Role=self.role_arn,
            Command={
                'Name': 'glueetl',
                'PythonVersion': '3'
            },
            DefaultArguments={
                '--enable-glue-datacatalog': 'true',
                '--job-language': 'python'
            },
            MaxCapacity=2.0,
            Timeout=60
        )
        
        self.session_id = response['Session']['Id']
        print(f"✅ Session created: {self.session_id}")
        
        self._wait_for_session_ready()
        return self.session_id
    
    def _wait_for_session_ready(self):
        """세션이 READY 상태가 될 때까지 대기"""
        print("⏳ Waiting for session to be ready...")
        
        while True:
            response = self.glue.get_session(Id=self.session_id)
            state = response['Session']['Status']
            
            if state == 'READY':
                print("✅ Session is ready!")
                break
            elif state in ['FAILED', 'STOPPED']:
                raise Exception(f"Session failed: {state}")
            
            time.sleep(5)
    
    def run_spark_code(self, code):
        """Spark 코드 실행"""
        if not self.session_id:
            raise Exception("Session not created. Call create_session() first.")
        
        print(f"📝 Running Spark code...")
        
        response = self.glue.run_statement(
            SessionId=self.session_id,
            Code=code
        )
        
        statement_id = response['Id']
        return self._wait_for_statement_complete(statement_id)
    
    def _wait_for_statement_complete(self, statement_id):
        """Statement 실행 완료 대기"""
        print("⏳ Waiting for statement to complete...")
        
        while True:
            response = self.glue.get_statement(
                SessionId=self.session_id,
                Id=statement_id
            )
            
            state = response['Statement']['State']
            
            if state == 'AVAILABLE':
                output = response['Statement'].get('Output', {})
                print("✅ Statement completed!")
                return output
            elif state in ['ERROR', 'CANCELLED']:
                error = response['Statement'].get('Output', {})
                raise Exception(f"Statement failed: {error}")
            
            time.sleep(2)
    
    def delete_session(self):
        """세션 종료"""
        if self.session_id:
            print(f"🗑️  Deleting session: {self.session_id}")
            self.glue.delete_session(Id=self.session_id)
            print("✅ Session deleted")


# 사용 예제
if __name__ == "__main__":
    # EC2 인스턴스 프로파일 사용 (role_arn 생략)
    client = GlueSparkClient()  # ← role_arn 없이 호출
    
    # 또는 명시적으로 role_arn 제공
    # client = GlueSparkClient(role_arn="arn:aws:iam::123456789012:role/GlueServiceRole")
    
    try:
        # 세션 생성
        client.create_session('my-analysis-session')
        
        # Spark 코드 실행
        result = client.run_spark_code("""
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        
        df = spark.read.csv('s3://sungbum-bigdata-test/big_transaction/HI-Medium_Trans.csv', header=True)
        print(f"Total rows: {df.count()}")
        df.show(5)
        """)
        
        print("Result:", result)
        
    finally:
        client.delete_session()
