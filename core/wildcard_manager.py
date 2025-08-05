# core/wildcard_manager.py

import os
from pathlib import Path

class WildcardManager:
    def __init__(self):
        self.wildcards_dir = os.path.join(os.getcwd(), 'wildcards')
        self.wildcard_dict_tree = {}
        self.reload_callbacks = []
        self.activate_wildcards()

    def activate_wildcards(self):
        """
        [수정됨] os.walk를 사용하여 모든 하위 폴더를 재귀적으로 탐색하고
        와일드카드 딕셔너리를 구축합니다.
        """
        if not os.path.exists(self.wildcards_dir):
            os.makedirs(self.wildcards_dir)
            try:
                print(f"📁 와일드카드 디렉토리 생성: {self.wildcards_dir}")
            except UnicodeEncodeError:
                print(f"[DIR] 와일드카드 디렉토리 생성: {self.wildcards_dir}")

        self.wildcard_dict_tree.clear() # 매번 새로고침을 위해 초기화

        # os.walk로 wildcards_dir의 모든 파일과 폴더를 순회합니다.
        for root, dirs, files in os.walk(self.wildcards_dir):
            for file in files:
                if file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    
                    # wildcards_dir를 기준으로 상대 경로를 계산합니다.
                    # 예: 'wildcards/characters/outfit.txt' -> 'characters/outfit.txt'
                    relative_path = os.path.relpath(file_path, self.wildcards_dir)
                    
                    # 와일드카드 이름 생성 (확장자 제거 및 경로 구분자 통일)
                    # 예: 'characters\\outfit.txt' -> 'characters/outfit'
                    wildcard_name = Path(relative_path).with_suffix('').as_posix()
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # 비어있지 않은 라인만 리스트에 추가
                            lines = [line.strip() for line in f if line.strip()]
                        
                        if lines:
                            self.wildcard_dict_tree[wildcard_name] = lines
                        else:
                            try:
                                print(f"⚠️ 와일드카드 파일이 비어있습니다: {file_path}")
                            except UnicodeEncodeError:
                                print(f"[WARN] 와일드카드 파일이 비어있습니다: {file_path}")
                            
                    except Exception as e:
                        try:
                            print(f"❌ 와일드카드 파일 읽기 오류 {file_path}: {e}")
                        except UnicodeEncodeError:
                            print(f"[ERROR] 와일드카드 파일 읽기 오류 {file_path}: {e}")

        try:
            print(f"✅ {len(self.wildcard_dict_tree)} 개의 와일드카드 로드 완료.")
        except UnicodeEncodeError:
            print(f"[OK] {len(self.wildcard_dict_tree)} 개의 와일드카드 로드 완료.")
        
        # 등록된 콜백 함수들을 호출하여 리로드 이벤트를 알림
        for callback in self.reload_callbacks:
            try:
                callback(len(self.wildcard_dict_tree))
            except Exception as e:
                try:
                    print(f"❌ 와일드카드 리로드 콜백 실행 중 오류: {e}")
                except UnicodeEncodeError:
                    print(f"[ERROR] 와일드카드 리로드 콜백 실행 중 오류: {e}")

    def reload_wildcards(self):
        """
        와일드카드를 다시 로드합니다. 파일 변경사항을 반영하기 위해 사용합니다.
        """
        try:
            print("🔄 와일드카드 리로드 중...")
        except UnicodeEncodeError:
            print("[RELOAD] 와일드카드 리로드 중...")
        self.activate_wildcards()
        
    def register_reload_callback(self, callback):
        """
        와일드카드 리로드 시 호출될 콜백 함수를 등록합니다.
        콜백 함수는 와일드카드 개수를 인자로 받습니다.
        """
        if callback not in self.reload_callbacks:
            self.reload_callbacks.append(callback)
            
    def unregister_reload_callback(self, callback):
        """
        등록된 리로드 콜백 함수를 제거합니다.
        """
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)
            
    def get_wildcard_count(self):
        """
        현재 로드된 와일드카드 개수를 반환합니다.
        """
        return len(self.wildcard_dict_tree)