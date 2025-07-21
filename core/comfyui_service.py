# core/comfyui_service.py
import json
import uuid
import asyncio
import websocket
import requests
import time
from typing import Dict, Any, Optional, Callable
from PIL import Image
from io import BytesIO
from typing import List
import threading

class ComfyUIService:
    """ComfyUI API 통신을 담당하는 서비스 클래스"""
    
    def __init__(self, server_url: str = "127.0.0.1:8188"):
        self.server_url = server_url.rstrip('/')
        if not self.server_url.startswith('http'):
            self.server_url = f"http://{self.server_url}"
        
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self.progress_callback: Optional[Callable] = None
        
    def connect_websocket(self) -> bool:
        """WebSocket 연결 설정 (수정된 버전)"""
        try:
            ws_url = self.server_url.replace('http', 'ws') + f"/ws?clientId={self.client_id}"
            
            # 🔧 수정: websocket-client 라이브러리 올바른 사용법
            self.ws = websocket.create_connection(ws_url, timeout=10)
            print(f"✅ ComfyUI WebSocket 연결 성공: {ws_url}")
            return True
        except Exception as e:
            print(f"❌ ComfyUI WebSocket 연결 실패: {e}")
            self.ws = None
            return False
    
    def disconnect_websocket(self):
        """WebSocket 연결 해제"""
        if self.ws:
            try:
                self.ws.close()
                print("✅ ComfyUI WebSocket 연결 해제")
            except:
                pass
            self.ws = None
    
    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """진행률 콜백 함수 설정"""
        self.progress_callback = callback
    
    def test_connection(self) -> bool:
        """ComfyUI 서버 연결 테스트"""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=5)
            if response.status_code == 200:
                print("✅ ComfyUI 서버 연결 성공")
                return True
            else:
                print(f"❌ ComfyUI 서버 응답 오류: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ ComfyUI 서버 연결 실패: {e}")
            return False
    
    def queue_workflow(self, workflow: Dict[str, Any]) -> Optional[str]:
        """워크플로우를 실행 큐에 추가"""
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.server_url}/prompt",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get('prompt_id')
                if prompt_id:
                    print(f"✅ 워크플로우 큐 등록 성공: {prompt_id}")
                    return prompt_id
                else:
                    print("❌ 응답에서 prompt_id를 찾을 수 없음")
                    return None
            else:
                print(f"❌ 워크플로우 큐 등록 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ 워크플로우 큐 등록 중 예외 발생: {e}")
            return None
    
    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> bool:
        """워크플로우 완료 대기 (폴링 방식으로 변경)"""
        print(f"🔄 워크플로우 완료 대기 시작: {prompt_id}")
        
        start_time = time.time()
        last_progress = 0
        
        # WebSocket 연결 시도 (실패해도 폴링으로 대체)
        ws_connected = self.connect_websocket()
        
        try:
            while time.time() - start_time < timeout:
                # 1. WebSocket으로 실시간 진행률 확인 (가능한 경우)
                if ws_connected and self.ws:
                    try:
                        # 0.1초 타임아웃으로 논블로킹 체크
                        self.ws.settimeout(0.1)
                        message = self.ws.recv()
                        
                        if message:
                            data = json.loads(message)
                            msg_type = data.get('type')
                            
                            if msg_type == 'progress':
                                progress_data = data.get('data', {})
                                value = progress_data.get('value', 0)
                                max_value = progress_data.get('max', 100)
                                
                                if self.progress_callback:
                                    self.progress_callback(value, max_value)
                                
                                last_progress = value
                                print(f"🔄 진행률: {value}/{max_value}")
                            
                            elif msg_type == 'executing':
                                executing_data = data.get('data', {})
                                node_id = executing_data.get('node')
                                
                                if node_id is None:
                                    print("✅ 워크플로우 실행 완료 (WebSocket)")
                                    return True
                                else:
                                    print(f"🔄 노드 실행 중: {node_id}")
                            
                            elif msg_type == 'execution_error':
                                error_data = data.get('data', {})
                                print(f"❌ 실행 오류: {error_data}")
                                return False
                    
                    except websocket.WebSocketTimeoutException:
                        # 타임아웃은 정상 (논블로킹)
                        pass
                    except Exception as ws_e:
                        print(f"⚠️ WebSocket 오류, 폴링으로 전환: {ws_e}")
                        ws_connected = False
                        self.disconnect_websocket()
                
                # 2. HTTP 폴링으로 완료 상태 확인 (1초마다)
                if int(time.time() - start_time) % 1 == 0:  # 1초마다 체크
                    try:
                        response = requests.get(f"{self.server_url}/history/{prompt_id}", timeout=5)
                        
                        if response.status_code == 200:
                            history = response.json()
                            
                            if prompt_id in history:
                                result = history[prompt_id]
                                status = result.get('status', {})
                                
                                # 완료 상태 확인
                                if status.get('status_str') == 'success':
                                    print("✅ 워크플로우 실행 완료 (HTTP 폴링)")
                                    return True
                                elif status.get('status_str') == 'error':
                                    print(f"❌ 워크플로우 실행 실패: {status}")
                                    return False
                                
                                # 진행률 업데이트 (WebSocket이 없는 경우)
                                if not ws_connected and self.progress_callback:
                                    # 간단한 추정 진행률
                                    elapsed = time.time() - start_time
                                    estimated_progress = min(int((elapsed / 60) * 100), 95)  # 최대 95%까지
                                    if estimated_progress > last_progress:
                                        self.progress_callback(estimated_progress, 100)
                                        last_progress = estimated_progress
                    
                    except Exception as poll_e:
                        print(f"⚠️ 폴링 체크 실패: {poll_e}")
                
                # 0.1초 대기
                time.sleep(0.1)
            
            print("❌ 워크플로우 완료 대기 시간 초과")
            return False
            
        except Exception as e:
            print(f"❌ 워크플로우 완료 대기 중 예외 발생: {e}")
            return False
        finally:
            # 정리
            if ws_connected:
                self.disconnect_websocket()
    
    def get_generation_result(self, prompt_id: str) -> List[Dict[str, Any]]:
        """
        [수정] 생성 결과를 조회하고, ID가 가장 높은(가장 마지막으로 간주)
        이미지 노드의 결과만 찾아 리스트로 반환합니다.
        """
        image_results = []
        try:
            response = requests.get(f"{self.server_url}/history/{prompt_id}", timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 생성 결과 조회 실패: {response.status_code}")
                return []

            history = response.json()
            if prompt_id not in history:
                return []

            result = history[prompt_id]
            outputs = result.get('outputs', {})
            
            # 1. 이미지를 실제로 생성한 노드들만 필터링합니다.
            image_producing_nodes = {}
            for node_id, node_output in outputs.items():
                if 'images' in node_output and isinstance(node_output['images'], list):
                    # node_id를 정수로 변환하여 저장 (비교를 위해)
                    image_producing_nodes[int(node_id)] = node_output['images']
            
            if not image_producing_nodes:
                print("❌ 생성 결과에서 이미지 정보를 찾을 수 없음")
                return []

            # 2. 찾은 노드들 중에서 ID가 가장 높은 노드를 선택합니다.
            last_node_id = max(image_producing_nodes.keys())
            
            # 3. 해당 노드의 이미지 정보만 최종 결과 리스트에 추가합니다.
            last_node_images = image_producing_nodes[last_node_id]
            for image_info in last_node_images:
                 image_results.append({
                     'filename': image_info.get('filename'),
                     'subfolder': image_info.get('subfolder', ''),
                     'type': image_info.get('type', 'output'),
                     'source_node_id': str(last_node_id) # 다시 문자열로 변환하여 반환
                 })

            print(f"✅ 최종 이미지 노드(ID: {last_node_id})에서 {len(image_results)}개의 결과를 찾았습니다.")
            return image_results

        except Exception as e:
            print(f"❌ 생성 결과 조회 중 예외 발생: {e}")
            return []
    
    def download_image(self, filename: str, subfolder: str = '', image_type: str = 'output') -> Optional[Image.Image]:
        """
        [수정] 생성된 이미지를 다운로드하고, PIL 객체와 원본 바이트를 함께 반환합니다.
        """
        try:
            params = {
                'filename': filename,
                'type': image_type
            }
            
            if subfolder:
                params['subfolder'] = subfolder
            
            response = requests.get(
                f"{self.server_url}/view",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                raw_bytes = response.content
                print(f"✅ 이미지 다운로드 성공: {filename}")
                return image, raw_bytes
            else:
                print(f"❌ 이미지 다운로드 실패: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 이미지 다운로드 중 예외 발생: {e}")
            return None
    
    def generate_image(self, workflow: Dict[str, Any], progress_callback: Optional[Callable] = None) -> Optional[Dict[str, Any]]:
        """완전한 이미지 생성 파이프라인"""
        if progress_callback:
            self.set_progress_callback(progress_callback)
        
        print("🚀 ComfyUI 이미지 생성 시작")
        
        # 1. 워크플로우 큐에 추가
        prompt_id = self.queue_workflow(workflow)
        if not prompt_id:
            return {'status': 'error', 'message': '워크플로우 큐 등록 실패'}
        
        # 2. 실행 완료 대기
        if not self.wait_for_completion(prompt_id, timeout=180):
            return {'status': 'error', 'message': '워크플로우 실행 실패 또는 시간 초과'}
        
        # 3. 결과 조회 (이제 리스트를 반환받음)
        # [수정] 변수명을 복수형(result_infos)으로 변경하여 리스트임을 명시
        result_infos = self.get_generation_result(prompt_id)
        if not result_infos:
            return {'status': 'error', 'message': '생성 결과 조회 실패'}
        
        # [핵심 수정] 반환된 리스트에서 첫 번째 결과(딕셔너리)를 선택합니다.
        first_image_info = result_infos[0]
        
        # 4. 이미지 다운로드 (선택된 딕셔너리를 사용)
        download_result = self.download_image(
            first_image_info['filename'],
            first_image_info.get('subfolder', ''),
            first_image_info.get('type', 'output')
        )
        
        if download_result:
            image, raw_image_bytes = download_result
            
            return {
                'status': 'success',
                'image': image,
                'raw_bytes': raw_image_bytes,
                'prompt_id': prompt_id,
                'filename': first_image_info['filename']
            }
        else:
            return {'status': 'error', 'message': '이미지 다운로드 실패'}
    
    def get_available_models(self) -> List[str]:
        """사용 가능한 모델 목록 조회"""
        try:
            response = requests.get(f"{self.server_url}/object_info", timeout=10)
            
            if response.status_code == 200:
                object_info = response.json()
                checkpoint_loader = object_info.get('CheckpointLoaderSimple', {})
                input_info = checkpoint_loader.get('input', {})
                required_info = input_info.get('required', {})
                ckpt_name_info = required_info.get('ckpt_name', [])
                
                if isinstance(ckpt_name_info, list) and len(ckpt_name_info) > 0:
                    return ckpt_name_info[0]  # 첫 번째 요소가 모델 리스트
                
            print("❌ 모델 리스트 조회 실패")
            return []
            
        except Exception as e:
            print(f"❌ 모델 리스트 조회 중 예외 발생: {e}")
            return []
    
    def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """시스템 상태 조회"""
        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"❌ 시스템 상태 조회 실패: {e}")
            return None