import io
from contextlib import redirect_stdout
import random
import re
import math

class SafeExecutor:
    """
    제한된 환경에서 안전하게 파이썬 코드를 실행하는 샌드박스 클래스.
    'random', 're', 'math'와 같은 안전한 모듈의 사용을 허용합니다.
    """
    def __init__(self, allowed_vars: dict):
        # 실행에 사용할 변수들은 복사하여 원본을 보호
        self.allowed_vars = {k: v.copy() for k, v in allowed_vars.items()}
        
        # ✅ 2. 허용할 모듈들을 딕셔너리로 정의합니다.
        # 사용자는 'import' 없이 'random.choice()'처럼 바로 사용할 수 있습니다.
        self.allowed_modules = {
            'random': random,
            're': re,
            'math': math
        }
        
        safe_builtins = {
            'print': self.captured_print, 'len': len, 'str': str, 'int': int, 
            'float': float, 'list': list, 'dict': dict, 'set': set, 
            'tuple': tuple, 'range': range, 'abs': abs, 'min': min, 
            'max': max, 'sum': sum, 'sorted': sorted, 'isinstance': isinstance,
            'True': True, 'False': False, 'None': None,
        }

        # ✅ 3. 실행 환경의 전역 변수에 허용된 모듈들을 추가합니다.
        self.execution_globals = {
            "__builtins__": safe_builtins,
            **self.allowed_vars,
            **self.allowed_modules
        }
        self.output_buffer = io.StringIO()

    def captured_print(self, *args, **kwargs):
        print(*args, file=self.output_buffer, **kwargs)

    def execute(self, code: str):
        """사용자 코드를 안전하게 실행하고 결과와 변경된 변수를 반환합니다."""
        
        # ✅ 4. 'import'와 'from'을 금지 목록에서 제거합니다.
        #    대신 dunder method 접근을 막는 '__'는 유지하여 보안을 강화합니다.
        forbidden_keywords = ['eval', 'exec', 'open', 'getattr', 'setattr', 'delattr', '__']
        if any(keyword in code for keyword in forbidden_keywords):
            return "오류: 허용되지 않는 키워드가 포함되어 있습니다.", None, False

        self.output_buffer.seek(0)
        self.output_buffer.truncate(0)

        try:
            # 실행 전 컨텍스트의 모든 태그를 집합(set)으로 만듦
            initial_all_tags = set(self.allowed_vars.get('prefix_tags', [])) | \
                               set(self.allowed_vars.get('main_tags', [])) | \
                               set(self.allowed_vars.get('postfix_tags', []))

            # ✅ 5. 실행을 위한 로컬/전역 환경을 설정합니다.
            #    전역 환경에는 이미 allowed_vars와 allowed_modules가 포함되어 있습니다.
            execution_locals = {}
            
            # 코드 실행
            exec(code, self.execution_globals, execution_locals)

            # 실행 후 변경된 변수들의 최종 상태를 가져옴
            updated_vars = {}
            for key in self.allowed_vars.keys():
                # 로컬 스코프에서 변경된 값을 우선적으로 반영합니다.
                if key in execution_locals:
                    updated_vars[key] = execution_locals[key]
                elif key in self.execution_globals:
                    updated_vars[key] = self.execution_globals[key]


            # 실행 후 컨텍스트의 모든 태그를 집합(set)으로 만듦
            final_all_tags = set(updated_vars.get('prefix_tags', [])) | \
                             set(updated_vars.get('main_tags', [])) | \
                             set(updated_vars.get('postfix_tags', []))

            # '진짜로 제거된' 태그 계산 (초기 상태에는 있었지만, 최종 상태에는 없는 태그)
            truly_removed_tags = initial_all_tags - final_all_tags

            # 최종 removed_tags 목록 업데이트
            # (기존 removed_tags 목록 + 진짜로 제거된 태그 목록)
            final_removed_set = set(updated_vars.get('removed_tags', [])).union(truly_removed_tags)
            updated_vars['removed_tags'] = sorted(list(final_removed_set))

            output = self.output_buffer.getvalue()
            return output, updated_vars, True

        except Exception as e:
            return f"실행 중 오류 발생: {e}", None, False