# DEV-ANALYZER-TRACE-007-EVIDENCE — 가상 분석기의 주파수 trace 계약

2026-10-24, Asia/Seoul. 총괄이 P01 한 창구에 배정한다. 선언 frequency source 다음 단위에서 기존 scalar signal_analyzer에 별도 trace 출력을 연결할 때 필요한 입력·유효성·완료 경계를 기존 확보 자료로 확인한다. 수집 전체 완료나 새 원문 확보를 기다리는 요청이 아니다.

## 우선순위와 범위

현재 공개 catalog의 N9030A 두 profile, FSV40 및 FSV(10 Hz ~ 40 GHz) profile을 대상으로 **최대12행**의 작은 근거 행렬을 만든다. 모델 이름이 같다고 option/application/firmware·지원 명령을 같게 취급하지 않는다. 정확한 모델·매뉴얼 판본이 매칭되지 않는 행은 unknown으로 남긴다.

기존 확보 공식 매뉴얼/장비 metadata를 먼저 사용한다. 이번 예산은 신규 원문·네트워크·계정/구매·장비/시험장 검색·실물 명령·원문 body 전달 모두 0이다. 필요한 근거가 없으면 해당 빈칸/후속 후보만 반환하고 자료가 없다는 이유로 가상 source 개발을 막지 않는다. 개별 수집자 배정/검수/패키징은 P01이 수행한다.

## 필요한 행과 완료 조건

행별 최소값은 대상 profile/model, 문서 ID/hash·edition/date·쪽/section, 조건/옵션/firmware 미확정, 확인한 의미와 unsupported/unknown 경계다. 명령 문자열이 기존 자료에 있을 때만 짧게 참조한다.

- trace의 주파수 축: start/stop/center/span·points와 실제 빈 개수/순서/단위의 관계.
- trace 수치: absolute power/density/relative 값의 구별, detector·RBW/VBW/window·normalization 의미와 명시하지 못하는 항목.
- trigger/acquire/fetch/completion·cached trace·설정 변경 후 stale/invalid 의미. OPC만으로 새 유효 취득을 입증할 수 있는지와 확인되지 않은 조건.
- binary/ASCII 전송의 shape·길이·단위/endianness 같은 기존 확인 범위. 실제 protocol 운전을 수행하지 않는다.

명령 에뮬레이터의 지원 완료·계측 정확도·규범 방법 승인으로 표시하지 않는다. 현재 scalar 결과에서 RF trace/nominal BW를 추론하거나 DUT 모드 사실을 보강하지 않는다. matrix/reference/gaps/validation과 고정 index의 bytes/SHA로 P01 검수 사본을 반환한다. 원문·이미지·실측 수치/serial·개인 경로/비밀은 공개 Git에 넣지 않는다. 사용자에게 새 암호/raw/계정·실물 연결을 요구하지 않는다.
