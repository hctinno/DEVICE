# 보존 conducted 비교 CLI

2026-10-26 Asia/Seoul. `DEV3-CONDUCTED-COMPARISON-CLI-001`의 범위는 명시한 네 JSON snapshot을 읽어 [비교 API](conducted_twin_comparison_usage.md)를 한 번 호출하고 그 DTO를 출력하는 단일 CLI다. 합성·실측·재생은 제공된 origin 표기를 유지하며 CLI가 실측 진위나 사용 권한을 인증하지 않는다.

```text
python -B -m labflow.virtual_fleet.conducted_twin_comparison_cli --result-file result.json --reference-file reference.json --policy-file policy.json --lineage-file lineage.json
python -B -m labflow.virtual_fleet.conducted_twin_comparison_cli --help
```

네 옵션을 각각 한 번, 분리된 값과 함께 전달한다. 순서는 자유다. 기본 경로·자동 탐색·디렉터리 입력·환경변수 선택·인수 파일·`--option=value`는 지원하지 않는다. 상대 경로는 호출 시 현재 디렉터리 기준이다. `--result-file`은 D3 `conducted_twin_result` JSON이며 e3 writer의 manifest가 아니다. CLI가 manifest를 따라가거나 다른 파일을 선택하지 않는다. 올바른 JSON이지만 의미가 맞지 않으면 비교 API가 `not_assessed`를 반환한다.

Windows native 파일 읽기를 사용한다. 네 경로는 로컬 일반 파일이어야 한다. UNC·장치 경로·drive-relative·상위 이동·reparse 경로를 거부한다. 각 경로의 부모와 조상 디렉터리 identity를 확인하고 파일을 읽기 전용으로 pin한다. 합계 raw 입력은 2 MiB 이하이며 UTF-8 BOM, 잘못된 UTF-8, 중복 키, 비유한 수, 고립 surrogate, 과도한 중첩을 거부한다. JSON 공백·키 순서·마지막 LF 유무는 제한하지 않는다. 네 snapshot에 새 측정치·허용오차·단위·plane·lineage·규범값을 추가하지 않는다.

pin된 native descriptor와 경로의 identity, 크기, 수정 시각, 파일 형식 및 raw bytes를 읽기 전후와 비교 API 이후 확인한다. 최종 검사가 끝나면 알려진 owned handle을 정리한 뒤 출력한다. 출력은 그 검사 시점의 snapshot이며 handle 해제 후 파일이 계속 같은 상태라는 보장은 하지 않는다. 이 검사는 참조가 가리키는 원본 증거나 실장비 상태를 확인하지 않는다. 하위 참조는 열지 않는다.

stdout은 부모의 exact11 DTO를 그대로 compact·키 정렬 JSON으로 한 번 write하고 LF 하나를 붙인다. 전체 UTF-8 출력은 LF 포함 256 KiB 이하다. 추가 envelope·새 평가·숫자 보정·표시용 반올림·오류의 성공 전환은 없다. `comparison.within_tolerance=false`도 비교가 성립한 결과다. 규격 합격·부적합 판정으로 바꾸지 않는다. 부모의 `source_bytes="not_reopened"`와 `execution_authority=false`를 유지한다.

| 종료 | 의미 | stdout |
| --- | --- | --- |
| 0 | `compared` 또는 help | 비교 DTO 또는 help |
| 3 | 의미·근거 부족으로 `not_assessed` | 숫자가 보류된 비교 DTO |
| 4 | 파일·JSON·크기·동일성·부모 응답·정리 오류 | 없음 |
| 2 | 인수 형식 오류 | 없음 |
| 1 | 출력 전달 오류 | 부분 전달 가능 |
| 130 | 최초 오류가 KeyboardInterrupt | 단계에 따라 없음 또는 부분 전달 |

운영 오류는 `{"error":{"code":"conducted_twin_comparison_cli_<code>"}}` 한 줄을 stderr에 시도한다. 고정 code는 `invalid_argument`, `path_invalid`, `not_found`, `input_limit`, `json_invalid`, `input_changed`, `unavailable`, `output_failed`, `interrupted`다. 경로·입력값·임의 예외 메시지를 출력하지 않는다. 최초 오류를 정리·진단 출력의 후속 오류로 덮어쓰지 않는다. API·stdout write를 재시도하지 않는다.

직접 호출하는 `main(argv)`는 호출자의 stream을 닫거나 교체·재설정하지 않는다. 모듈 실행은 해당 프로세스의 stdout/stderr만 UTF-8 strict/LF로 설정한다. BrokenPipe와 마지막 flush 실패는 조용한 종료 처리를 사용하며 앞선 파일 오류·취소 종료를 보존한다.

실행·저장·재평가·outcome 복구·StoreSQL·HTTP·AI·실장비 제어를 연결하지 않는다. 입력의 의미 검증과 산술·lineage 정책은 기존 비교 API가 담당한다. 이 CLI의 검증은 새 disposable 합성 예시, native 파일 경계, 인수·stream·취소 fault injection, 실제 로컬 Python 모듈 자식 프로세스로 한정한다. 기존 비교 26, 수치 12, 보류 5, RF 101의 분모를 합치거나 다시 실행하지 않는다. 실측·현장·기관 적합성은 미검증이다.

신규 CLI 검사 33개를 통과했다. 실제 모듈 child 5건은 비교 0·보류 3·누락 파일 4·닫힌 stdout 1·help 0이며, 비교 API 호출은 각각 1·1·0·1·0회다. child의 입력 raw와 native metadata가 전후 동일함을 확인했다. UTF-8 설정은 cp949 초기 환경과 임의 작업 디렉터리에서도 확인했다. 실제 pin 중 쓰기·rename은 거부됐으며, 같은 stamp의 raw 변경·API 이후 파일 소실·reparse attribute는 명명된 주입 검사다. 실제 junction·symlink 교체와 전역 handle 누수 검증은 수행하지 않았다.
