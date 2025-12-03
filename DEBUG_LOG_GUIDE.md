# 디버그 로그 삭제 가이드

## 디버그 로그 식별 방법

이 프로젝트에서는 추후 삭제 가능한 디버그 로그에 `[DEBUG]` 주석을 추가했습니다.

### 검색 방법

1. **파일 전체 검색**:
   ```bash
   grep -n "\[DEBUG\]" backend/expense_automation/groupware_bot.py
   ```

2. **IDE에서 검색**:
   - `[DEBUG]` 또는 `# [DEBUG]`로 검색

### 디버그 로그 종류

- `[DEBUG]`: 일반 디버그 로그 - 삭제 가능
- `[DEBUG 상세]`: 상세한 디버그 로그 - 삭제 가능
- `[DEBUG] 처리 여부 확인`: 처리 여부 확인 관련 로그 - 삭제 가능

### 삭제 시 주의사항

- 오류 로그 (❌, ⚠️)는 유지
- 성공 로그 (✅)는 유지
- 중요한 진행 상황 로그는 유지
- 디버그 로그만 삭제

### 예시

```python
# [DEBUG] 매칭 시도 로그 - 추후 삭제 가능
print(f"   매칭 시도: 웹 금액={current_amount_clean}")

# [DEBUG] 금액 추출 로그 - 추후 삭제 가능
print(f"   웹 금액 {i+1}: {cell.text} -> {cell_amount}")

# [DEBUG] 처리 여부 확인 로그 - 추후 삭제 가능
print(f"        행 {row_index+1}은 이미 처리됨 (span 데이터: {', '.join(span_contents)})")
```

### 유지해야 할 로그

- 오류 발생 로그
- 성공 완료 로그
- 주요 단계 완료 로그
- 사용자에게 중요한 정보 로그

