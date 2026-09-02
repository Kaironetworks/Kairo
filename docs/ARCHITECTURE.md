# KAIRO Architecture

KAIRO is split into an application/data plane and a separate trust plane.

```text
React/Vite
   │
   ▼
FastAPI
   ├── JWT authentication
   ├── RBAC / permission enforcement
   ├── evidence lifecycle
   ├── audit orchestration
   └── governance
   │
   ├───────────────┐
   ▼               ▼
PostgreSQL       MinIO / S3-compatible storage
metadata         evidence bytes
   │               │
   └───────┬───────┘
           ▼
     KAIRO trust ledger
           │
           ▼
     Fabric Gateway
           │
           ▼
 Hyperledger Fabric
```

Evidence bytes remain off-chain.

The repository currently implements JWT authentication and a JavaScript Fabric chaincode package. Keycloak/OIDC and Go chaincode are not represented as completed implementation claims unless separately integrated and verified.
