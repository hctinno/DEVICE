# read048-managed-storage-v1

이 버전은 RF reader의 source 위치와 managed artifact 저장소를 구분한 IO 개정이다. 계산·기기·규범·실모델 실행 승인이 아니며 기존 19파일 engine과 두 역사 observation pin tuple을 바꾸지 않는다.

현재 writer의 정적 source 계약은 `labflow/virtual_fleet/managed_reader_source_version.py`의 `SOURCE_VERSION`과 `SOURCE_PINS`다. 파일을 실제로 읽어 LF로 정규화한 크기/SHA를 다음 **하나의 coherent tuple**과 대조한다. runtime에 관측한 hash를 자동으로 수용하지 않는다.

| role | LF bytes | SHA-256 |
|---|---:|---|
| read048 | 26502 | f8c75251910a241bcc4557fe74c034c3e554726334f42f98cbab1d7ef0c6f77a |
| describe041 | 44423 | f5471dde9786983152992e04fa2dade8b5ac927b1c25e5c0303c30bb664db1aa |
| waveform054 | 7581 | 7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d |
| native_helper | 29100 | 8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7 |

새 bundle의 `provenance`에 `dependency_source_version="read048-managed-storage-v1"`과 정확한 4핀을 함께 기록한다. 기존 writer `_PINS`와 readonly reader의 과거 `_PINS`·`_CURRENT_PINS`는 보존한다.

Readonly 검증은 다음을 구별한다.

- 과거 버전 표지가 없는 기록은 원래의 두 역사 tuple 중 하나여야 한다. 원 bytes·hash·필드를 추가·변경하지 않는다.
- 새 버전 표지가 있는 기록은 위 이름과 새 4핀 전부가 같아야 한다.
- unknown 이름, 새 tuple의 무표지 기록, 과거 tuple을 새 버전으로 표시한 기록, 서로 다른 버전의 핀 혼합은 거절한다.

현재 실행에 과거 reader code를 로드하면 새 source gate에서 거절한다. 과거 JSON이 읽힌다는 이유로 현재 source 검증을 통과시키지 않는다. 기존 source/native handle·identity·변경 탐지·출력 독점 생성·read-only 검사는 유지한다.

관측된 별도 공백은 그대로 남는다. 최초 원본 19파일의 normalized engine SHA456b9c1d…와 frozen expected7816f87d…의 불일치는 이 reader 개정으로 수용하거나 다시 쓰지 않는다. 새 source gate 뒤 실제 reader 호출 `[1,0,0,0]`에 도달한 후 그 원래 engine mismatch에서 중단되는지 별도로 검증한다. source pin 자체에서 `[0,0,0,0]`으로 닫히는 것과 같은 결과로 집계하지 않는다.
