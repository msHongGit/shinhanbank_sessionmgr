"""
Session Manager - Batch API Tests (v4.0)
VDB → SM
Sprint 1: Mock Repository 사용
"""

from datetime import UTC, datetime


class TestBatchProfileUpload:
    """배치 프로파일 업로드 테스트"""

    def test_batch_upsert_profiles(self, client, vdb_headers):
        """프로파일 배치 업로드 성공"""
        request = {
            "batch_id": "batch_001",
            "source_system": "VDB",
            "computed_at": datetime.now(UTC).isoformat(),
            "records": [
                {"user_id": "user001", "attributes": [{"key": "segment", "value": "VIP", "source_system": "VDB"}]},
                {"user_id": "user002", "attributes": [{"key": "segment", "value": "GOLD", "source_system": "VDB"}]},
            ],
        }

        response = client.post("/api/v1/batch/profiles", json=request, headers=vdb_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["processed_count"] == 2
