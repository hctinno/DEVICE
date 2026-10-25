# Vertex REST 응답 생산 어댑터

2026-10-25, Asia/Seoul. [공통 설계](../superpowers/specs/2026-10-25-vertex-ai-connection-design.md)와 [계획](../superpowers/plans/2026-10-25-vertex-ai-connection.md)에 따른 [구현](../../labflow/vertex_response.py)·[합성 검사](../../tests/test_vertex_response.py)다. 선택 의존성은 [requirements-vertex.txt](../../requirements-vertex.txt)의 google-auth 2.62.0·requests 2.34.2이며 기본 의존성을 변경하지 않는다.

이 모듈은 호출자가 명시한 authorized_user ADC 파일과 고정 settings를 사용해 REST v1 generateContent를 한 번 시도한다. 기본 ADC 탐색, gcloud, 환경변수의 자격 증명·프록시, Google Gen AI SDK, API 키, 자동 재시도·redirect·continuation은 사용하지 않는다. 실제 권한·무료 체험 잔액·만료·호출 예산은 host가 호출 전에 확인하고 예약한다. metadata 검사나 UI 설정 저장이 이 권한을 부여하지 않는다.

## API와 고정 입력

```python
inspect_vertex_credentials(adc_path: Path, *, settings: dict) -> dict

produce_vertex_response(
    prompt_bytes: bytes,
    response_schema_bytes: bytes,
    *,
    settings: dict,
    adc_path: Path,
    evidence_dir: Path,
    cancel_event: threading.Event | None = None,
) -> tuple[bytes, dict]
```

bytes·dict는 정확한 native type이다. Path는 해당 OS의 정확한 `type(Path())`인 절대 경로이고 ADC는 regular file이어야 한다. symlink·Windows reparse 및 해당 부모 경로를 거절한다. evidence_dir은 기존 디렉터리를 덮지 않는 새 경로이며 부모는 이미 있어야 한다. cancel_event는 None 또는 정확한 native threading.Event다. 입력과 ADC 파일을 수정하지 않는다.

settings의 정확16키는 schema_version, kind, profile_id, profile_revision, provider, service, project_id, location, quota_project_id, auth_profile_id, model_id, thinking_level, max_output_tokens, timeout_seconds, profile_sha256, settings_sha256이다. schema_version=1, kind=ai_run_settings, provider=vertex_ai, service=aiplatform.googleapis.com, project와 quota는 모두 `project-a6310591-f8cc-487c-9e3`여야 한다. 설정 hash는 settings_sha256을 제외한 canonical UTF-8 JSON의 SHA-256으로 다시 확인한다. profile_sha256은 형식을 검사하며 원 프로필과의 연결·CAS는 프로필 소유 모듈과 host가 관리한다.

허용 모델은 gemini-4-argon·gemini-3.8-flash, thinking은 LOW·MEDIUM·HIGH, location은 global·us·eu다. output은 bool 아닌 정수64..8192, timeout은 유한한 native 숫자1..120초다. profile/auth ID는 ASCII 식별자 최대128자, revision은 bool 아닌 비음수 signed64 정수다. 원격에서 모델 사용을 실제 확인한 상태와 이 입력 허용 목록을 구별한다.

prompt는 canonical UTF-8 JSON object·최대256KiB이고 schema는 원래 공백을 보존하는 UTF-8 JSON object·최대64KiB다. 중복 키·비유한 수·잘못된 Unicode·과도한 구조를 거절한다. schema를 provider의 responseJsonSchema로 변환하지 않는다. 원 prompt/schema 문자열 두 개를 user content의 JSON wrapper에 넣고 generationConfig에는 maxOutputTokens·thinkingConfig.thinkingLevel만 보낸다. prompt의 expected_producer도 그대로 유지된다.

global은 aiplatform.googleapis.com, us/eu는 각각 aiplatform.us.rep.googleapis.com·aiplatform.eu.rep.googleapis.com을 사용한다. [공식 location 자료](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations?hl=en)에 따른 host이며 임의 region이나 provider fallback을 선택하지 않는다. thinking enum의 근거는 [Argon 가이드](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon)와 [Flash 모델 자료](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash)에 있다.

## 인증·시간·응답 경계

inspect는 명시 ADC를 최대64KiB로 읽고 authorized_user 형상·필수 비밀 필드 존재·quota·고정 token endpoint·universe를 확인한다. 정확11키의 vertex_credentials_metadata를 반환하며 refresh_attempted/model_access_verified/credit_status_verified는 false다. refresh·네트워크·자식 프로세스·파일 쓰기는 0이다. ADC 경로·account·client ID·secret·token·인증 응답을 반환하거나 보존 파일에 넣지 않는다.

produce는 입력·metadata 확인 후 증거 디렉터리를 배타 생성하고 spawn 자식 하나에서 명시 refresh를 수행한다. OAuth POST는 고정 https://oauth2.googleapis.com/token 한 번, 생성 POST도 한 번이다. google-auth가 인증을 다시 요청하면 두 번째 송신 전에 차단한다. 요청의 x-goog-user-project도 고정 quota와 같다. 인증 body는 메모리에서 최대64KiB까지만 읽고 저장하지 않는다.

부모는 50ms 이하 간격으로 취소·monotonic 전체 deadline·자식 종료를 확인한다. timeout에는 증거 준비 이후 import·refresh·생성·본문 수집이 포함된다. requests의 connect/read timeout은 남은 시간 이내이며 connect는 최대10초다. 종료가 필요하면 terminate/join2초, 이어서 필요할 때 kill/join2초를 수행한다. 파일·상태 회수도 bounded 크기로 수행한다. 회수 실패는 성공이 아니며 로컬 중단이 원격 취소·무과금을 입증하지 않는다. 별도 프로세스의 종료는 고정 오류로 기록하고, 부모에서 발생한 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 정리 후 원 객체를 전파한다.

생성 raw body는 64KiB chunk로 최대2MiB와 초과 판별1byte까지만 저장한다. non-identity Content-Encoding은 거절한다. HTTP200·완료된 본문·정상 자식 종료·정제 상태·시작/완료 기록이 모두 필요하다. [공식 응답 계약](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/GenerateContentResponse)에 따라 candidate는 정확1개, content.role=model, finishReason=STOP이어야 한다. safety 차단·MAX_TOKENS·continuation·tool/function·미지 finish·여러 candidate·잘못된 JSON/UTF-8·부분 응답을 정상 bytes로 반환하지 않는다.

thought=true인 part는 최종 응답에서 제외한다. 나머지 text part는 순서대로 구분자 없이 합쳐 원 bytes를 반환한다. fence 제거·JSON 수선·기본 사실 채우기·업무 결과 검증은 하지 않는다. [기존 strict decoder](intake_model_boundary_usage.md)가 별도로 최종 분석 형상·producer·context·인용을 검사한다. raw generation body에는 thought·provider 오류 내용이 포함될 수 있으므로 증거 디렉터리는 host의 비공개 경로에 둔다.

## Receipt와 실패 증거

반환 receipt는 정확18키의 분리된 native dict다. schema_version/kind/exchange_ref/status/failure, bindings, settings, client, request, attempts, response, usage, cost, timing, cancellation, cleanup, artifacts, verification을 포함한다. 성공은 vertex_response_receipt·complete·wire_complete=true이며 성공 artifact6개와 모든 시작/완료·회수 기록을 요구한다. requested model과 provider가 보고한 modelVersion은 별개다. remote_identity_verified/semantic_quality_verified/credit_verified는 계속 false다.

attempts의 worker·refresh·auth HTTP·generation은 각각0/1 또는 관측 불가 null이다. 중간 종료 후 송신 여부가 불명확하면 generation을0으로 채우지 않는다. 비용은 입증된 generation0일 때만 not_applicable, 그 외 unknown이고 amount/currency/price_version은 null이다. usage가 없으면 null이며 제공된 여섯 token 수 중 빠진 값도 null이다. 비어 있는 사용량·timeout·취소를 과금0이나 예산 환급으로 해석하지 않는다.

| artifact 키 | 상대 파일 | 내용 |
|---|---|---|
| prompt | request.json | 원 prompt bytes |
| response_schema | response-schema.json | literal schema bytes |
| settings | settings.json | 고정 settings canonical bytes |
| provider_request | provider-request.json | 실제 생성 요청 payload |
| provider_response | provider-response.bin | 생성 raw body 또는 bounded prefix |
| final_text | response-text.bin | 추출한 최종 text bytes |

descriptor는 path/present/bytes/sha256/complete/overflow/extent 정확7키다. prefix SHA는 수집한 첫 bytes만의 hash이며 완전한 원격 응답 hash가 아니다. 별도 receipt.json과 내부 고정 marker·worker-result.json도 같은 비공개 디렉터리에 기록한다. 실패·부분 파일은 삭제하거나 성공값으로 교체하지 않는다.

VertexResponseError의 code/str/args는 고정 코드만 담고 cause/context는 없다. receipt는 증거 폴더 생성 전이면 null, 이후에는 가능한 failed 사본이다. 첫 오류를 유지하고 정리 오류는 cleanup.secondary_errors에 별도로 남긴다. receipt 저장 실패 때는 메모리의 partial receipt만 제공될 수 있다. 고정 prefix vertex_response_의 suffix16은 invalid_input, invalid_settings, credential_invalid, credential_quota_mismatch, dependency_unavailable, evidence_error, auth_failed, http_error, response_invalid, incomplete, blocked, limit_exceeded, timeout, cancelled, cleanup_failed, internal_error다.

## 기존 분석 경계와의 조립

아래 함수의 호출 전에 host가 실제 호출 권한·무료 체험 gate·누적 예산을 확인하고 예약해야 한다. 최초 실제 묶음의 한도는 모델2×thinking3 최대6회·각512 token·누적3072·각60초 이내·전체300초이며 host가 관리한다. 어댑터의 독립 호출은 이 누적 gate를 대신하지 않는다. Windows spawn을 사용하는 실행 진입점은 `if __name__ == "__main__":`로 보호한다.

```python
import json
from labflow.intake_model_boundary import build_analysis_prompt, decode_analysis_response
from labflow.vertex_response import produce_vertex_response


def run_reserved_analysis(context, *, settings, adc_path, evidence_dir, schema_bytes, cancel_event):
    producer_name = "vertex-trial"
    prompt = build_analysis_prompt(context, producer_name=producer_name)
    prompt_bytes = json.dumps(
        prompt, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    raw_response, receipt = produce_vertex_response(
        prompt_bytes, schema_bytes, settings=settings,
        adc_path=adc_path, evidence_dir=evidence_dir,
        cancel_event=cancel_event,
    )
    analysis = decode_analysis_response(raw_response, context, producer_name=producer_name)
    return analysis, receipt
```

## 검사 범위

```powershell
python -B -X utf8 -m unittest discover -s tests -p test_vertex_response.py -v
python -B -X utf8 -m unittest discover -s tests -p test_intake_model_boundary.py -v
python -B -X utf8 scripts/check_artifacts.py
```

전용 검사는 합성 ADC·실제 로컬 spawn·모의 HTTP/session/auth를 사용하고 실제 socket 연결을 차단한다. 모델2×thinking3의 입력/요청 결합, host3, 잘못된 입력·metadata·HTTP/응답·부분/초과, 인증 재송신 차단, 취소·시간초과·시작 직후 control, 정리 실패·첫 오류·비밀 미포함을 검사한다. 실제 ADC·refresh·모델 생성은0회다. 이 결과는 실제 모델 연결·의미 품질·RF/EMC/SAR 실측·현장·기관 적합성·전체 무인화 완료 증거가 아니다. 총괄의 독립 검수와 고정 실제 묶음은 별도 실행이다.
