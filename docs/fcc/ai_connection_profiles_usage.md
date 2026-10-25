# Vertex AI 연결 프로필과 실행 설정

이 모듈은 비밀정보 없는 연결 설정을 로컬 JSON으로 저장하고, 실행에 사용할 설정을 분리된 `dict`로 확정한다. 인증, 모델 호출, SDK 설치, 환경변수 조회, Store·HTTP·화면 변경은 수행하지 않는다. 구현은 [ai_connection_profiles.py](../../labflow/ai_connection_profiles.py), 검사는 [test_ai_connection_profiles.py](../../tests/test_ai_connection_profiles.py)에 있다.

## 모델과 기본값

2026-10-25 Asia/Seoul 확인 기준으로 Google 공식 문서는 두 모델의 `LOW`·`MEDIUM`·`HIGH`와 기본 `MEDIUM`을 명시한다. 모델 ID와 `global`·`us`·`eu`는 각 모델 카드에서 확인했다. 이는 문서상의 지원 범위이며 해당 프로젝트의 호출 권한이나 크레딧 상태를 입증하지 않는다. [Thinking](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking), [Gemini 4 Argon](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/4-argon), [Gemini 3.8 Flash](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash).

| 항목 | 초기값 / 허용값 |
| --- | --- |
| provider / 실행 service | `vertex_ai` / `aiplatform.googleapis.com` |
| project_id / quota_project_id | 둘 다 `project-a6310591-f8cc-487c-9e3` |
| profile_id / auth_profile_id | 둘 다 `vertex-trial` |
| location | 기본 `global`, 허용 `global`·`us`·`eu` |
| selected_model | 기본 `gemini-3.8-flash` |
| models | 정확히 `gemini-4-argon`, `gemini-3.8-flash` 각각의 설정 |
| thinking_level | 모델마다 기본 `MEDIUM`, 허용 `LOW`·`MEDIUM`·`HIGH` |
| max_output_tokens | 모델마다 기본 `512`, 정수 `64..8192` |
| timeout_seconds | 모델마다 기본 `60`, 유한한 정수/실수 `1..120`초 |

토큰·시간 범위는 이 로컬 기능의 제한이다. 공급자 최대값이나 응답 시간 보장은 아니다. `MINIMAL`, `OFF`, `thinking_budget`, 별칭·`-latest` 모델, AI Studio provider/fallback, 알 수 없는 옵션, 자동 값 치환을 허용하지 않는다. 프로젝트 이름은 안전한 로컬 문자열 형식만 검사하며 실제 존재·IAM·과금 적합성을 조회하지 않는다.

## API와 사용

```python
load_profile(path) -> dict
save_profile(path, profile, *, expected_revision) -> dict
resolve_run_settings(profile, *, model_id=None, overrides=None) -> dict
```

`path`는 호출자가 선택한 기존 private 로컬 디렉터리 안의 `str` 또는 `pathlib.Path`다. 상대 경로는 호출자의 현재 디렉터리를 기준으로 한다. 디렉터리를 자동으로 만들지 않는다. GUI 연결 시 호스트가 정한 경로를 사용하고, 요청 본문으로 임의의 파일 경로를 받지 않는다. 디렉터리 접근 권한은 호출자가 관리한다. Windows에서는 상속되는 디렉터리 ACL을 확인해야 하며 이 모듈은 ACL을 변경하지 않는다.

```python
from pathlib import Path
from labflow.ai_connection_profiles import (
    load_profile, save_profile, resolve_run_settings,
)

# private_directory는 호출자가 미리 선택·준비한 디렉터리다.
path = Path(private_directory) / 'vertex-profile.json'
profile = load_profile(path)
expected = profile['revision']
profile['models']['gemini-4-argon']['thinking_level'] = 'HIGH'
profile['models']['gemini-3.8-flash']['thinking_level'] = 'LOW'
profile['selected_model'] = 'gemini-3.8-flash'
saved = save_profile(path, profile, expected_revision=expected)

# 이 실행만 Argon/MEDIUM/1024. 저장된 HIGH·LOW 값은 그대로다.
run_settings = resolve_run_settings(
    saved, model_id='gemini-4-argon',
    overrides={'thinking_level': 'MEDIUM', 'max_output_tokens': 1024},
)
```

파일이 없으면 `load_profile`은 새 기본값과 `revision=0`을 반환한다. 프로필 파일은 생성하지 않지만 잠금 sidecar는 만들 수 있다. 파일이 존재하는데 깨졌다면 기본값으로 대체하지 않고 `corrupt`를 반환한다. 첫 저장은 `expected_revision=0`, 성공 반환은 `revision=1`이다. 이후 저장은 읽어온 revision을 그대로 제출하며 성공할 때마다 정확히 1 증가한다. 입력 객체는 변경하지 않는다. 기존 파일의 `profile_id` 변경은 거절한다. 다른 프로필은 별도 경로에 revision 0으로 시작한다.

`model_id=None`이면 `selected_model`을 사용한다. 명시한 잘못된 모델은 거절한다. `overrides`는 `None` 또는 `thinking_level`·`max_output_tokens`·`timeout_seconds`의 부분집합인 일반 `dict`다. 모델·프로젝트·provider·위치·인증 참조를 override로 바꿀 수 없다. 두 모델의 저장 설정과 실행별 override는 서로 섞이지 않는다.

## 저장 JSON

최상위 키는 정확히 10개다. `models`는 정확히 두 모델을 가지며 각 모델은 정확히 세 설정 키를 가진다. 아래는 최초 저장 뒤의 예시다.

```json
{
  "schema_version": 1,
  "profile_id": "vertex-trial",
  "provider": "vertex_ai",
  "project_id": "project-a6310591-f8cc-487c-9e3",
  "location": "global",
  "quota_project_id": "project-a6310591-f8cc-487c-9e3",
  "auth_profile_id": "vertex-trial",
  "selected_model": "gemini-3.8-flash",
  "models": {
    "gemini-4-argon": {"thinking_level": "MEDIUM", "max_output_tokens": 512, "timeout_seconds": 60},
    "gemini-3.8-flash": {"thinking_level": "MEDIUM", "max_output_tokens": 512, "timeout_seconds": 60}
  },
  "revision": 1
}
```

`schema_version`은 정수 1, revision은 정수 `0..9007199254740991`이다. 디스크에 존재하는 파일은 revision 1 이상이어야 한다. `bool`은 모든 숫자 위치에서 거절한다. `profile_id`·`auth_profile_id`는 ASCII 영숫자로 시작하는 1..128자의 영숫자·`_`·`-`, project/quota는 1..128자의 소문자 영숫자·`-`이며 양 끝이 영숫자여야 한다. 경로, URL, 공백, 제어 문자, 점, 비ASCII 문자를 ID에 넣을 수 없다.

일반 `dict` 이외의 객체, 누락·추가 키, 중복 JSON 키, `NaN`·`Infinity`, 범위 밖 숫자, 형 변환이 필요한 문자열은 거절한다. 읽기는 BOM 없는 UTF-8, 최대 16,384바이트로 제한한다. 손상 파일의 원본 바이트를 자동 수정하거나 덮어쓰지 않는다.

프로필과 실행 DTO에는 credential 파일 경로·내용, access/refresh token, API key, billing account 필드가 없다. `auth_profile_id`는 안전한 참조 ID이며 자격증명 자체가 아니다. 인증 조회와 실제 호출은 별도의 명시된 연결 담당 범위다.

## 실행 스냅샷 exact16

| 키 | 의미 |
| --- | --- |
| schema_version / kind | `1` / `ai_run_settings` |
| profile_id / profile_revision | 검증한 원 프로필 식별자 / revision |
| provider / service | `vertex_ai` / `aiplatform.googleapis.com` |
| project_id / location / quota_project_id / auth_profile_id | 검증·복사한 연결 값 |
| model_id | 해당 실행에서 선택한 정확한 모델 ID |
| thinking_level / max_output_tokens / timeout_seconds | 해당 모델의 저장값에 실행 override를 적용한 값 |
| profile_sha256 | 두 모델 설정과 revision을 포함한 전체 프로필의 canonical SHA-256 |
| settings_sha256 | 자신을 제외한 나머지 15개 실행 키의 canonical SHA-256 |

반환값은 scalar만 가진 **분리된 plain dict**다. 원 프로필·override·다른 실행 결과와 alias가 없다. 여기서 불변 스냅샷은 실행 시 검증·복사한 값과 해시를 실행 기록에 보존한다는 뜻이다. Python 변경 차단 객체나 인증·보안 증거가 아니다. 호출자는 반환값을 수정하지 않고 실행 기록에 함께 보존해야 한다. 반환 dict를 나중에 수정하면 그 값은 기존 해시의 대상과 달라진다.

Canonical은 `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')`다. 숫자를 자동 형 변환하지 않으므로 `60`과 `60.0`의 JSON 표현과 해시는 다를 수 있다. 키 순서는 해시에 영향을 주지 않는다.

## 잠금·충돌·오류

load/save는 `<프로필 파일명>.lock`에 비차단 OS 잠금을 사용한다. Windows는 `msvcrt`, POSIX는 `fcntl`을 사용한다. 잠금 파일은 영구 유지하며 프로세스 종료 시 OS 잠금은 해제된다. 사용 중인 sidecar를 삭제해서는 안 된다. 대기·재시도·병합·stale lock 제거는 하지 않는다. 서로 협조하는 로컬 호출자를 위한 범위이며 네트워크 파일시스템이나 악성 사용자가 디렉터리를 바꾸는 상황은 보장하지 않는다.

경로의 `..`, UNC, 제어 문자, Windows 장치 이름·끝 점/공백·ADS 문자, 심볼릭 링크/reparse 경로, hardlink, 디렉터리·기타 비정규 파일을 거절한다. 잠금 sidecar에도 정규 파일·단일 링크 검사를 적용한다.

Windows의 8.3 짧은 별칭은 같은 파일에 다른 sidecar를 만들 수 있으므로 지원하지 않는다. `GetLongPathNameW`로 존재하는 대상과 부모 경로의 긴 이름을 확인하고 대소문자 차이만 허용한다. 없는 파일도 부모를 확인한다. 경로 성분의 `~`는 파일 생성 전부터 예약하여 거절하며, 교체 직전에도 대상을 다시 확인한다. `~`가 없는 짧은 이름도 가능하므로 이 문자 검사만으로 판정하지 않는다. 긴 이름을 확인할 수 없으면 `invalid_path`로 닫힌다. [Microsoft 긴 이름 조회](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getlongpathnamew), [짧은 이름 조회와 파일시스템별 생성 조건](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getshortpathnamew).

저장은 잠금 안에서 현재 revision을 읽고 입력 revision·expected_revision·현재 revision의 일치를 확인한 뒤 같은 디렉터리의 임시 파일에 쓰고 flush/fsync 후 atomic replace한다. 교체 후 잠금 안에서 재조회한다. 잘못된 입력·CAS 충돌·잠금 실패는 마지막 정상 프로필을 보존한다. 교체 이후의 I/O 오류는 새 revision이 이미 저장된 상태일 수 있으므로 반드시 재조회해서 확인한 후 다음 동작을 정한다. 전원 상실 시의 완전한 내구성은 검증하지 않았다.

`AIConnectionProfileError(ValueError)`는 `.code`와 동일한 고정 메시지만 반환한다. 아래 표의 접미사 앞에 `ai_connection_profile_`가 붙는다. 입력값·경로·내부 OS 오류 내용은 메시지에 포함하지 않는다. `KeyboardInterrupt`·`SystemExit`는 동일 객체로 전파한다.

| 접미사 | 의미 |
| --- | --- |
| invalid_path | 허용되지 않는 경로·파일 형식 또는 존재하지 않는 부모 |
| invalid_profile | 입력 프로필·실행 override·모델·기존 profile_id 변경이 잘못됨 |
| invalid_revision | expected_revision 형식·범위가 잘못됨 |
| revision_conflict | 입력·기대·현재 revision 불일치 |
| locked | 다른 호출자가 OS 잠금을 보유 중 |
| corrupt | 기존 파일의 UTF-8·JSON·중복·크기·스키마 손상 |
| storage_error | 기타 I/O 오류 또는 교체 후 확인 실패 |
| revision_exhausted | revision 상한에 도달하여 증가 불가 |

## 검증 범위

실행 명령은 `python -m unittest discover -s tests -p test_ai_connection_profiles.py -v`다. 기본값·모델별 저장·override 분리·canonical 해시·형식/수치/비밀키 거절·손상 보존·CAS·실제 하위 프로세스의 OS 잠금/종료 해제·동시 writer·cold 재조회 및 replace/fsync/control fault를 검사한다. fault 주입 결과와 실제 파일/프로세스 결과는 구별한다. Windows symlink 생성 권한이 없는 환경에서는 해당 검사만 명시 skip하며 별도 실제 junction으로 reparse 부모 거절을 검사한다.

8.3 검사는 OS가 실제 생성한 짧은 이름과 긴 이름의 파일 ID가 같은지 확인한 뒤 잠금 우회 거절, 부모 별칭, 생성 전·재생성 후 거절을 검사한다. 실제 8.3 이름이 없는 환경은 명시 skip하며 통과로 간주하지 않는다. 긴 이름 조회 실패·`~` 없는 이름의 변환·fsync 이후 교체 직전 재확인은 별도 fault 검사다.

이 로컬 검사와 문서 무결성 검사는 실제 인증·모델 응답·과금·무료 크레딧·실장비·계측 정확도·기관 적합성 검증이 아니다. 실제 모델 호출은 이 모듈에서 0회다.
