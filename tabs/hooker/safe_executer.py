import io
from contextlib import redirect_stdout
import random
import re
import math
import builtins

class SafeExecutor:
    """
    최소 제약 파이썬 코드 실행기.
    OS 접근 및 위험한 함수만 차단하고, 나머지는 모두 허용.
    """
    def __init__(self, allowed_vars: dict):
        self.allowed_vars = {k: v.copy() for k, v in allowed_vars.items()}

        # 허용 모듈
        self.allowed_modules = {
            'random': random,
            're': re,
            'math': math
        }

        # 위험한 함수/키워드만 블랙리스트로 관리
        self.blacklisted_keywords = [
            'import os', 'from os', '__import__', 'exec', 'eval', 'compile',
            'open(', 'file(', 'input(', 'raw_input(',
            'subprocess', 'system', 'popen', 'spawn',
            'exit(', 'quit(', 'sys.exit',
            'delattr', '__del__', '__class__', '__bases__', '__subclasses__',
            'globals()', 'locals()', 'vars()', 'dir()',
            'getattr', 'setattr', 'hasattr'
        ]

        # 모든 기본 내장 함수를 허용 (위험한 것들만 제외)
        dangerous_builtins = {
            'open', 'input', 'raw_input', 'file', 'execfile', 'reload', 
            'exit', 'quit', '__import__', 'eval', 'exec', 'compile',
            'delattr', 'getattr', 'setattr', 'hasattr', 'globals', 'locals', 'vars', 'dir'
        }
        
        # 모든 내장 함수에서 위험한 것들만 제외
        safe_builtins = {}
        for name in dir(builtins):
            if not name.startswith('_') and name not in dangerous_builtins:
                safe_builtins[name] = getattr(builtins, name)
        
        # 기본적으로 필요한 상수들 추가
        safe_builtins.update({
            'True': True,
            'False': False,
            'None': None,
            'print': self.captured_print,
            # 기본 예외 클래스들도 허용
            'Exception': Exception,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'IndexError': IndexError,
            'KeyError': KeyError,
            'AttributeError': AttributeError,
        })

        self.execution_globals = {
            "__builtins__": safe_builtins,
            **self.allowed_vars,
            **self.allowed_modules
        }

        self.output_buffer = io.StringIO()

    def captured_print(self, *args, **kwargs):
        print(*args, file=self.output_buffer, **kwargs)

    def execute(self, code: str):
        """사용자 코드를 안전하게 실행"""
        # 블랙리스트 검사 (대소문자 구분 없이)
        code_lower = code.lower()
        for keyword in self.blacklisted_keywords:
            if keyword.lower() in code_lower:
                return f"오류: 보안상 허용되지 않는 키워드가 포함되어 있습니다: {keyword}", None, False

        self.output_buffer.seek(0)
        self.output_buffer.truncate(0)

        try:
            initial_all_tags = set(self.allowed_vars.get('prefix_tags', [])) | \
                               set(self.allowed_vars.get('main_tags', [])) | \
                               set(self.allowed_vars.get('postfix_tags', []))

            execution_locals = {}

            with redirect_stdout(self.output_buffer):
                exec(code, self.execution_globals, execution_locals)

            updated_vars = {}
            for key in self.allowed_vars.keys():
                if key in execution_locals:
                    updated_vars[key] = execution_locals[key]
                elif key in self.execution_globals:
                    updated_vars[key] = self.execution_globals[key]

            final_all_tags = set(updated_vars.get('prefix_tags', [])) | \
                             set(updated_vars.get('main_tags', [])) | \
                             set(updated_vars.get('postfix_tags', []))

            truly_removed_tags = initial_all_tags - final_all_tags
            final_removed_set = set(updated_vars.get('removed_tags', [])).union(truly_removed_tags)
            updated_vars['removed_tags'] = sorted(list(final_removed_set))

            output = self.output_buffer.getvalue()
            return output, updated_vars, True

        except Exception as e:
            return f"실행 중 오류 발생: {e}", None, False