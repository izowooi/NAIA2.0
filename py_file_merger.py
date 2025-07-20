import os
import shutil

def merge_py_files():
    """
    현재 디렉토리와 하위 디렉토리를 순회하며 .py 파일들을 찾아서
    디렉토리별로 합친 후 temp 폴더에 저장하는 함수
    """
    
    # temp 폴더 생성 (이미 존재하면 삭제 후 재생성)
    temp_dir = "temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # 현재 디렉토리부터 시작
    root_dir = "."
    
    # 각 디렉토리를 순회
    for root, dirs, files in os.walk(root_dir):
        # __pycache__ 폴더와 temp 폴더는 제외
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'temp', 'venv', 'not_implement']]
        
        # 현재 디렉토리에서 .py 파일 찾기
        if root == ".":
            # 시작 디렉토리에서는 NAIA_cold_v4.py만 읽기
            py_files = [f for f in files if f == 'NAIA_cold_v4.py']
        else:
            # 하위 디렉토리에서는 모든 .py 파일 읽기
            py_files = [f for f in files if f.endswith('.py')]
        
        if py_files:
            # 디렉토리 이름 결정
            if root == ".":
                dir_name = "main"
            else:
                # 경로에서 디렉토리 이름 추출 (상대 경로)
                dir_name = os.path.basename(root)
            
            # 합친 내용을 저장할 문자열
            merged_content = f"dir {dir_name}\n"
            
            # 각 .py 파일의 내용 읽기
            for py_file in sorted(py_files):
                file_path = os.path.join(root, py_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    merged_content += f"====== .py file name : {py_file} =======\n"
                    merged_content += content
                    if not content.endswith('\n'):
                        merged_content += '\n'
                    
                except UnicodeDecodeError:
                    # UTF-8로 읽기 실패 시 다른 인코딩으로 시도
                    try:
                        with open(file_path, 'r', encoding='cp949') as f:
                            content = f.read()
                        merged_content += f"====== .py file name : {py_file} =======\n"
                        merged_content += content
                        if not content.endswith('\n'):
                            merged_content += '\n'
                    except Exception as e:
                        merged_content += f"====== .py file name : {py_file} =======\n"
                        merged_content += f"# Error reading file: {str(e)}\n"
                
                except Exception as e:
                    merged_content += f"====== .py file name : {py_file} =======\n"
                    merged_content += f"# Error reading file: {str(e)}\n"
            
            # temp 폴더에 저장
            output_file = os.path.join(temp_dir, f"{dir_name}.py")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(merged_content)
            
            print(f"Created: {output_file}")
            print(f"  - Contains {len(py_files)} .py files from {root}")

def main():
    """메인 함수"""
    print("Python 파일 합치기 시작...")
    print("=" * 50)
    
    merge_py_files()
    
    print("=" * 50)
    print("완료! temp 폴더를 확인하세요.")

if __name__ == "__main__":
    main()