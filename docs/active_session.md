지금 까지 이야기 했던거 정리 하자면 아래와 같습니다.
일단 좀 더 쉽게 조회를 위해서, es index update 방식으로 갑니다.
호출해서 보는쪽에서 아래와 같이 조회하시면 된다고 하면 될거 같습니다.
우리는 적재/업데이트만 하면 됩니다.
 
세션 시작
 
{
  "session_id": "aaaaaaaa",
  "cusno": "603030201",
  "status": "start",
  "start_time": "시간",
  "end_time": null,
  "last_update": "시간"
}
 
 
세션 종료
 
{
  "session_id": "aaaaaaaa",
  "cusno": "603030201",
  "status": "end",
  "start_time": "시간",
  "end_time": "시간",
  "last_update": "시간"
}
 
 
ttl 만료 또는 종료 api 호출 시
 
def session_end(session_id):
    es.update(
        index="session_state",
        id=session_id,
        doc={
            "status": "end",
            "end_time": datetime.now(timezone.utc).isoformat(),
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    )
 
 
활성 세션 조회
파이썬 버전
 
def get_active_session_count():
    resp = es.count(
        index="session_state",
        query={
            "bool": {
                "must": [
                    {"term": {"status": "active"}},
                    {
                        "range": {
                            "start_time": {
                                "gte": "now-24h"
                            }
                        }
                    }
                ]
            }
        }
    )
    return resp["count"]
 
 
 
ES HTTP API 조회 버전
 
GET session_state/_count
{
  "query": {
    "bool": {
      "must": [
        {
          "term": {
            "status": "active"
          }
        },
        {
          "range": {
            "start_time": {
              "gte": "now-24h"
            }
          }
        }
      ]
    }
  }
}
 
 
 
 