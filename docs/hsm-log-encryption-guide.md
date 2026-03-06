# Session Manager — 로그 암호화 HSM 연동 가이드

> 작성일: 2026-03-06

---

## 개요

Session Manager 는 ES 로그(`eslog`, `agentlog`)의 `payload` 필드를
**Fernet(AES-128-CBC + HMAC-SHA256)** 으로 개별 암호화합니다.

암호화 키를 가져오는 방식은 환경변수 `HSM_ENABLED` 로 선택합니다.

| 환경 | `HSM_ENABLED` | 키 출처 |
|------|--------------|--------|
| 로컬 / 개발 | `false` (기본) | `LOG_ENCRYPTION_SECRET` → PBKDF2HMAC 파생 |
| on-prem 운영 | `true` | HSM PKCS#11 또는 고객사 암/복호화 SDK |

---

## 암호화 흐름

```
eslog(msg) / agentlog(msg)
  └─ encrypt_payload(msg.payload)   # ENCRYPT_EXCEPTIONS 키 제외
       └─ _get_encryption_key()
            ├─ HSM_ENABLED=false → PBKDF2HMAC(LOG_ENCRYPTION_SECRET)
            └─ HSM_ENABLED=true  → _get_key_from_hsm()
                                       ├─ [방식 1] PKCS#11# Session Manager — 로그 암호화 HSM 연동 가이드

> 작성일: 2026-03??
> 작성일: 2026-03-06

---

## 개요

Session Manager ??---

## 개요

Sessi lo
#er_
Sessiony  **Fernet(AES-128-CBC + HMAC-SHA만 고객사 SDK 에 맞게 교체
```

`e
암호화 키를 가져오는 방식은 환경변수 `HSM_ENABLED` ??| 환경 | `HSM_ENABLED` | 키 출처 |
|------|--------------|--------|
| 로컬 / ?=f|------|--------------|--------|
| 로?? 로컬 / 개발 | `false` (?E| on-prem 운영 | `true` | HSM PKCS#11 또는 고객사 암/복호화 SDK |

---

##T_
---

## 암호화 흐름

```
eslog(msg) / agentlog(msg)
  └─ encrypt_HSM
#???```
eslog(msg) / ??s??  └─ encrypt_payload(EN       └─ _get_encryption_key()
            ├─ HSM_ENABLED=fal  # K8s Secret 으로 주입
HSM_KEY_L            └─ HSM_ENABLED=true  → _get_key_from_hsm()
            ?                                      ├─ [방식 1] PK?> 작성일: 2026-03??
> 작성일: 2026-03-06

---

## 개요

Session Manager ??---

## 에 직접 기입하지 마세? 작성일: 2026-03-? 
---

## 개요

Sesconfi
#py`
Sessionet_
## 개요

Sessi lo
#를
Sessi l???er_
Se
#Ses?``

`e
암호화 키를 가져오는 방식은 환경변수 `HSM_ENABLED` s1
````?`|------|--------------|--------|
| 로컬 / ?=f|------|--------------|--------|
| 로?? 로컬 / 개발 | `fa??| 로컬 / ?=f|------|--------y_| 로?? 로컬 / 개발 | `false` (?E| on-p??
---

##T_
---

## 암호화 흐름

```
eslog(msg) / agentlog(msg)
  └─ encrypt_HSM
#???```
eslog(msg) / ??성
#? ?--??
#rom shinhan_crypto_sdk iesor  └─ encrypt_HSM
#????#???```
eslog(msg)
ceslog = C            ├─ HSM_ENABLED=fal  # K8s Secret 으로 ?api_key=os.getenv("CRYPTHSM_KEY_L            └─ HSM_ENABLED=true  → _get_key_frKE            ?                                      ├─ [방식 ??> 작성일: 2026-03-06

---

## 개요

Session Manager ??---

## 에 직접 기입하지 마삤
---

## 개요

Sessi? ?#입
Session-


## 에 직접 기입??---

## 개요

Sesconfi
#py`
Sessionet_
## 개요

SessiXC
#TIO
Sesconf???py`
Se??Ses??# 개요?Sessi l해#를
???es??Se
#Ses?``
? ?`e
암???실````?`|------|--------------|--------|
| 로컬 / ?=f|------|-----EP| 로컬 / ?=f|-----    "globId",
    "| 로?? 로컬 / 개발 | `fa??| 로컬 / ?= "---

##T_
---

## 암호화 흐름

```
eslog(msg) / agentlog(msg)
  └─ encrypt_HSM
#???```
eslog(msg) / ???
#?? ---?#
``
```
eslog(msg) / .yaes
a  └─ encrypt_HSM
#???
#???```
eslog(msg)eseslog(mna#? ?--??
#rom shin: #rom shitr#????#???```
eslog(msg)
ceslog = C            ELeslog(msg)
ce??eslog = M_
---

## 개요

Session Manager ??---

## 에 직접 기입하지 마삤
---

## 개요

Sessi? ?#입
Session-


## 에 직접 기입??---

## 개요

Sesconfi
#py`
Sessionet_
## 개요

SessiXC
#TIO
Sesconf???py`
Se??Ses??# 개요?Sessi : "
#
``
Sessiyaml

## 에 직접 기입?om---

## 개요

Sessi? ?#입
Sese
#ion
Sessi? -coSession-


#re

## ?   
## 개요

Sesconfi
#py`
-se
Sesconf

---

## ?es? ## 개요??SessiXC??TIO
S? Ses??Se??Ses??# ????es??Se
#Ses?``
? ?`e
암?Ses?``
? ? ?`eg.암???? | 로컬 / ?=f|------|-----EP| 로컬 / ?=f|--CS    "| 로?? 로컬 / 개발 | `fa??| 로컬 / ?= "---

##T_
?##T_
---

## 암호화 흐름

```
eslog(msg) / agentl()`---??# 2 
```
eslog(msg) / 암es?? └─ encrypt_HSM
#???`#???```
eslog(msg)??eslog(mPT#?? ---?#
``
`?`
```
esl??? es| a  └─ encrypt? #???
#???```
eslog?????eslog(m--#rom shin: #사항

- `HSM_PIN`eslog(msg)
ceslog = C            E?eslog = ??e??eslog = M_
---

## 개요

SEY---

## 개요??
#?? 
Sessi 1회
## 에 직접 기입???---

## 개요

Sessi? ?#입
Se??
#- H
Sessi? ? ?ession-


#?
## ????## 개요

Sesconfi
#py`
]` 
Sesconf???py`
합?es??## 개요EN
SessiXCABL#TIO
SseSes??Se??Ses??# ?#
``
Sessiyaml

## 에 직접서 S??
## 에 ??.
## 개요

Sessi? ?#입


`
Sessi? v rSese
#ion
Sest#ioniSeses

#re

## ?   
nit.py -v## 개??
Sesco? | ?py`
-s
|-se--Se-|
---

|
| TC-LS? Ses??Se??Ses??# ????es??Se
??#Ses?``
? ?`e
암?Ses?``an? ?`eTC암?S1 ? ? ?`eg.?o
##T_
?##T_
---

## 암호화 흐름

```
eslog(msg) / agentl()`---??# 2 
```
eslog(msg) / 암es?? └─ encrypt_HSM
#???y`?? ---

# m
# ?`?? 확인 |
