# 제목 없음

# NAIA - NAI Automation Tool

NAIA is distributed for Korean users. However, English is used throughout the system, making it easy to use. Please use a translator if necessary.

## 소개

NAIA는 Danbooru 데이터셋과 Automatic1111 (WEBUI/webui-forge/webui-reforge), Comfyui 기반의 Stable Diffusion API, 그리고 Novel AI Image Generation API를 이용하여 사용자가 프롬프팅에 큰 노력을 기울이지 않더라도 자동으로 이미지를 생성할 수 있도록 하는 자동화 툴 입니다. 

## 제공하는 기능 (Key features)

### Danbooru Random Prompt Generation

Danbooru 랜덤 프롬프트 생성 기능은 huggingface/isek-ai의 Danbooru 태그 데이터셋([isek-ai/danbooru-tags-2024 · Datasets at Hugging Face](https://huggingface.co/datasets/isek-ai/danbooru-tags-2024))을 이용하여 사용자가 희망하는 태그를 포함하고 있는 데이터셋의 General 행을 활용 해 Image 생성 API에게 전달할 프롬프트를 생성하는 기능을 수행합니다. 해당 기능은 하위 기능을 포함합니다:

```
**프롬프트 엔지니어링/자동화**
사용자가 검색을 통해 데이터셋으로 부터 정제된 Danbooru Dataset을 생성 했을 경우 [랜덤/다음 프롬프트 버튼]을 눌렀을 때 사용자가 미리 입력한 [선행 고정 프롬프트], [후행 고정 프롬프트], [자동 숨김 프롬프트], [프롬프트 전처리 옵션]을 이용하여 사용자 맞춤 프롬프트를 생성하도록 합니다. 해당 기능을 사용할 때 선행/후행 프롬프트 영역에 <와일드카드> 를 삽입할 수 있으므로 사용자는 매우 다양한 이미지를 생성 할 수 있습니다. 
```

## API Call Automation

NAIA는 각 이미지 생성 완료마다 **[자동화 설정] 기능을 참고하여 이번 이미지를 몇 번 반복하여 생성 할지, 아니면 몇 초 뒤에 다음 이미지를 생성할지 등을 결정**합니다. 특별히 자동화 설정을 하지 않았다면, 이미지 생성 완료 후 약 0.5초 뒤에 [랜덤/다음 프롬프트] 기능이 작동하며, 이후 [이미지 생성] 요청이 자동으로 진행됩니다. 사용자가 다른 서비스 제공자의 생성 API 서비스를 사용하지 않고, 사용자의 GPU 환경을 사용하는 Local Stable Diffusion API를 사용 할 때는 문제가 없습니다. 다른 API 서비스, **특히 Novel AI의 API 서비스를 사용할 때는 다음 규칙을 준수**하십시오: 

### Novel API 사용 시의 주의사항

NAIA는 NovelAI API를 통해 이미지 생성 기능을 제공합니다. 이 서비스를 이용하는 사용자는 NovelAI에서 정한 [이용 약관(Terms of Service)]과 [정책(Policy)]을 반드시 준수해야 합니다. NovelAI는 공식적으로 자사 API의 자동화 도구 연동을 허용하지 않았으며, 모든 사용자는 일반적인 이용자 수준에 준하는 호출 빈도를 유지하여 서비스 안정성을 해치지 않도록 주의할 책임이 있습니다.

NovelAI는 API 사용량이 과도하거나 정책을 위반하는 경우, 예고 없이 **429 (Too Many Requests)** 또는 **403 (Forbidden, 계정 영구 제한)** 상태 코드를 반환할 수 있으며, 이로 인한 불이익은 전적으로 사용자에게 책임이 있습니다. NAIA는 [자동화 설정] 기능을 통해 사용자가 API 호출량과 속도를 자율적으로 조절할 수 있는 기능을 제공하고 있습니다. 그러나 이 기능의 존재 여부와 관계없이, NovelAI API 사용 제한 또는 계정 정지 등과 관련된 모든 문제에 대해 NAIA는 책임을 지지 않습니다. * 추후 기능 개선 예정

## Generated Image Manager

[생성 결과] 탭에서 생성된 이미지를 쉽게 저장하거나 삭제하는 기능을 제공합니다. 필요한 경우, 사용자는 이미지 히스토리 영역의 썸네일을 우클릭하여 프롬프트를 재생성 할 수 있습니다. 이미지를 매 생성마다 자동 저장 하거나, WEBP 형태로 저장하거나, 혹은 일괄 저장 후 메모리를 정리하는 기능 등을 제공합니다. * 추후 기능 개선 예정

## Danbooru Search

[Danbooru] 탭에서 Danbooru 웹사이트에 접근할 수 있습니다. 각 Post 페이지에 진입하면 [태그 추출] 기능이 활성화 되어 특정 캐릭터의 핵심 프롬프트를 추출하거나, 또는 General 태그들을 받아올 수 있습니다. 사용자의 Local Storage에 쿠키를 저장하므로 Gold Account가 있는 사람은 유용하게 해당 기능을 사용할 수 있습니다. * 추후 기능 개선 예정

## PNG Info

Novel AI, Stable Diffusion 생성 이미지에 대한 EXIF View 기능을 제공합니다. 각종 WEB의 이미지 또한 Drag & Drop을 통해 처리할 수 있지만, 다운로드 속도가 제한되어 있는 웹사이트의 경우 프로그램이 장시간 멈출 수 있으므로 주의하세요. * 추후 기능 개선 예정

## Hooker

사용자는 NAIA의 프롬프트 생성 파이프라인의 작동 과정을 확인하고, 중간에 개입하거나 파이썬 스크립트 작성을 통해 사용자 필터 및 프롬프트 생성 알고리즘을 추가로 적용할 수 있습니다. * 추후 기능 개선 예정

## Storyteller

Storyteller는 사용자가 선호하는 프롬프트를 Shortcut 방식으로 저장하거나, 이러한 Shortcut들을 여러개 이어붙이는 것으로 마치 블록코딩을 하는 것 처럼 이미지 생성을 수행 할 수 있습니다. 또한, Cell 방식의 이미지 생성 블록을 여러개 이어붙여 연속적인 이미지를 생성 할 수 있습니다. * 추후 기능 개선 예정

## Deep Search

심층 검색은 좀 더 세분화된 데이터셋 정리를 원하시는 분들이 사용할 수 있는 기능입니다. 현재는 GUI를 바탕으로 기능을 제공하고 있으나, QScintilla를 이용하여 사용자가 직접 Pandas 명령어를 통해 Dataframe을 정제할 수 있도록 할 방침입니다. 

### 태그 검색 가이드라인

기본적인 사용 방식은 Danbooru의 이미지 검색과 동일하지만 공백 문자 ‘ ’ 를 쉼표 ‘, ’ 로 구분하고 언더바 ‘_’를 사용하지 않는 등의 차이가 있습니다. 사용자는 다음과 같이 키워드를 검색할 수 있습니다. 

```
단순 검색 : 1girl, solo -> 1girl과 solo 텍스트를 포함하는 모든 프롬프트. solo는 solo focus 혹은 solo leveling과 같은 태그를 포함할 수 있음.

퍼펙트 매칭 검색 : 1girl, *solo -> 1girl과 명확하게 solo 태그를 포함하는 모든 프롬프트. solo는 solo focus 혹은 solo leveling과 같은 태그를 포함하지 않음. 

OR 검색 : 1girl, {solo|pov} -> 1girl 텍스트는 무조건 포함하면서, solo 텍스트 또는 pov 텍스트를 포함하는 모든 플롬프트. {} 안의 텍스트는 *를 가질 수 없음

단순 제외 : boy, monochrome -> boy 텍스트와 monochrome 텍스트를 포함하는 모든 프롬프트를 검색 시 제외. 이로 인해 tomboy 등을 포함하는 프롬프트 또한 제외됨.

퍼펙트 제외 : ~1boy, multiple boys, monochrome -> 명확하게 1boy 태그를 포함하지 않으면서 multiple boys와 monochrome 텍스트 또한 포함하지 않는 프롬프트만 검색
```

# Installation

git을 통한 설치는 설명을 생략합니다. 

[https://github.com/DNT-LAB/NAIA2.0/archive/refs/heads/main.zip](https://github.com/DNT-LAB/NAIA2.0/archive/refs/heads/main.zip) 을 통해 압축파일을 다운로드 받은 뒤, 실행 대상 폴더에 압축 해제합니다.

### Windows

- 사용 전 [Python.org](http://Python.org) 에서 3.10.6 버전 이상의 Python을 설치합니다.
- Python 설치 시 Add Python To PATH 에 꼭 체크해야 합니다.
- 설치 완료 후 run_NAIA.bat 을 더블클릭하여 실행합니다.

### Mac os

- 사용 전 [Python.org](http://Python.org) 에서 3.10.6 버전 이상의 Python을 설치합니다.
- 아카이브 압축 해제 후 해당 디렉터리를 우클릭 하여 터미널에서 실행한 뒤 다음과 같이 입력합니다:

```
chmod +x run_NAIA.command
```

- 이후 run_NAIA.command 를 더블클릭 하면 실행 가능합니다.

### Linux

- 사용자는 프로그램 사용을 위한 구체적인 설명이 필요 없을 것 입니다.

## Initial Setup

[프롬프트 검색 / 필터링 / API 관리] 메뉴를 확장하여 [API 관리] 탭에 진입합니다. 각 항목에 접근하여 API 연동을 수행합니다. NovelAI 영구 토큰을 발급 받는 방법에 대해서는 Novel AI Persistent API Token 구글 검색을 해 주십시오. 이후 왼쪽 상단의 [ NAI / WEBUI / ComfyUI ] 토글 버튼을 전화하여 목적에 맞는 API를 사용하십시오. * 기본 설정은 Novel AI 입니다.
