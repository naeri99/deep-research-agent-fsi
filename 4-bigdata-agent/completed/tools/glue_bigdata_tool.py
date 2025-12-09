import boto3
import time
import logging
from typing import Any, Annotated
from strands.types.tools import ToolResult, ToolUse
from tools.decorators import log_io

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TOOL_SPEC = {
    "name": "glue_bigdata_tool",
    "description": "Use this to execute PySpark code on AWS Glue for big data analysis and calculation when dealing with large datasets (more than 500 MB). The code should use PySpark/Glue syntax. Include S3 paths directly in your code (e.g., spark.read.csv('s3://bucket/path/file.csv')). If you want to see the output of a value, you should print it out with `print(...)`. This is visible to the user",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The PySpark code to execute on AWS Glue for data analysis or calculation. Should use Glue/PySpark syntax and include S3 paths directly in the code (e.g., df = spark.read.csv('s3://my-bucket/data/file.csv'))."
                }
            },
            "required": ["code"]
        }
    }
}


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class GlueSparkClient:
    def __init__(self, region='ap-northeast-2'):
        self.glue = boto3.client('glue', region_name=region)
        self.sts = boto3.client('sts', region_name=region)
        self.session_id = None
        self.role_arn = self._get_role_from_instance_profile()

    def _get_role_from_instance_profile(self):
        try:
            identity = self.sts.get_caller_identity()
            arn = identity['Arn']

            if 'assumed-role' in arn:
                role_name = arn.split('/')[-2]
                account_id = identity['Account']
                return f"arn:aws:iam::{account_id}:role/{role_name}"
            else:
                raise Exception("Not running on EC2 with instance profile.")
        except Exception as e:
            raise Exception(f"Failed to get role from instance profile: {e}")

    def create_or_reuse_session(self, session_name='spark-session-third'):
        try:
            response = self.glue.get_session(Id=session_name)
            state = response['Session']['Status']
            
            if state == 'READY':
                print(f"{Colors.GREEN}[DEBUG] Reusing existing session: {session_name}{Colors.END}")
                self.session_id = session_name
                return self.session_id
            elif state in ['FAILED', 'STOPPED']:
                print(f"{Colors.YELLOW}[DEBUG] Session exists but is {state}, deleting and creating new one{Colors.END}")
                self.glue.delete_session(Id=session_name)
        except self.glue.exceptions.EntityNotFoundException:
            print(f"{Colors.BLUE}[DEBUG] Session not found, creating new one{Colors.END}")
        
        try:
            response = self.glue.create_session(
                Id=session_name,
                Role=self.role_arn,
                Command={'Name': 'glueetl', 'PythonVersion': '3'},
                DefaultArguments={
                    '--enable-glue-datacatalog': 'true',
                    '--job-language': 'python'
                },
                MaxCapacity=10.0,
                Timeout=120
            )
            self.session_id = response['Session']['Id']
        except Exception as e:
            if 'AlreadyExistsException' in str(e):
                print(f"{Colors.YELLOW}[DEBUG] Session already exists, reusing it{Colors.END}")
                self.session_id = session_name
                print(self.session_id)
            else:
                raise

        self._wait_for_session_ready()
        return self.session_id

    def _wait_for_session_ready(self):
        while True:
            response = self.glue.get_session(Id=self.session_id)
            state = response['Session']['Status']

            if state == 'READY':
                break
            elif state in ['FAILED', 'STOPPED']:
                raise Exception(f"Session failed: {state}")

            time.sleep(5)

    def run_spark_code(self, code):
        if not self.session_id:
            raise Exception("Session not created.")

        try:
            response = self.glue.run_statement(SessionId=self.session_id, Code=code)
            statement_id = response['Id']
            result = self._wait_for_statement_complete(statement_id)
            print(f"{Colors.BLUE}[DEBUG] Statement result: {result}{Colors.END}")
            return result
        except Exception as e:
            print(f"{Colors.RED}[ERROR] run_spark_code failed: {str(e)}{Colors.END}")
            raise

    def _wait_for_statement_complete(self, statement_id):
        while True:
            try:
                response = self.glue.get_statement(
                    SessionId=self.session_id,
                    Id=statement_id
                )

                state = response['Statement']['State']
                print(f"{Colors.YELLOW}[DEBUG] Statement state: {state}{Colors.END}")

                if state == 'AVAILABLE':
                    output = response['Statement'].get('Output', {})
                    print(f"{Colors.GREEN}[DEBUG] Statement output: {output}{Colors.END}")
                    return output
                elif state in ['ERROR', 'CANCELLED']:
                    error = response['Statement'].get('Output', {})
                    print(f"{Colors.RED}[ERROR] Statement failed with state {state}: {error}{Colors.END}")
                    raise Exception(f"Statement failed: {error}")

                time.sleep(2)
            except Exception as e:
                print(f"{Colors.RED}[ERROR] _wait_for_statement_complete exception: {str(e)}{Colors.END}")
                raise

    def delete_session(self):
        if self.session_id:
            self.glue.delete_session(Id=self.session_id)

# Global client instance
glue_client = None

@log_io
def handle_glue_bigdata_tool(
        code: Annotated[str, "The PySpark code to execute on AWS Glue with S3 paths included"]
):
    """
    Use this to execute PySpark code on AWS Glue for big data analysis and calculation.
    Include S3 paths directly in your code.
    """
    global glue_client

    print()
    logger.info(f"{Colors.GREEN}===== Executing PySpark code on Glue ====={Colors.END}")

    try:
        # Initialize client if needed
        if glue_client is None:
            print(f"{Colors.BLUE}[DEBUG] Creating new Glue client{Colors.END}")
            glue_client = GlueSparkClient()
            glue_client.create_or_reuse_session('bigdata-analysis-session-two')

        # Execute code
        print(f"{Colors.BLUE}[DEBUG] Executing code on Glue session{Colors.END}")
        result = glue_client.run_spark_code(code)

        # Truncate code to first 7 lines for context efficiency
        code_lines = code.split('\n')
        if len(code_lines) > 7:
            code_preview = '\n'.join(code_lines[:7])
            code_summary = f"{code_preview}\n... ({len(code_lines) - 7} more lines omitted)"
        else:
            code_summary = code

        result_str = f"Successfully executed:\n||{code_summary}||Output: {result}"
        logger.info(f"{Colors.GREEN}===== Code execution successful ====={Colors.END}")
        return result_str

    except BaseException as e:
        error_msg = f"Failed to execute. Error: {repr(e)}"
        logger.error(f"{Colors.RED}Failed to execute. Error: {repr(e)}{Colors.END}")
        print(f"{Colors.RED}[ERROR] Full traceback:{Colors.END}")
        import traceback
        traceback.print_exc()
        return error_msg

def glue_bigdata_tool(tool: ToolUse, **kwargs: Any) -> ToolResult:
    tool_use_id = tool["toolUseId"]
    code = tool["input"]["code"]

    result = handle_glue_bigdata_tool(code)

    if "Failed to execute" in result:
        return {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": result}]
        }
    else:
        return {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [{"text": result}]
        }

