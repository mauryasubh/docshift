# DocShift Multi-Cloud Architecture (AWS + Cloudflare)

This diagram visualizes how DocShift utilizes AWS ECS (Fargate) for compute, Cloudflare for edge routing and zero-egress file storage, and Serverless databases.

```mermaid
graph TD
    %% Define Styles
    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:white;
    classDef cloudflare fill:#F38020,stroke:#232F3E,stroke-width:2px,color:white;
    classDef client fill:#232F3E,stroke:#FF9900,stroke-width:2px,color:white;
    classDef db fill:#3b48cc,stroke:#232F3E,stroke-width:2px,color:white;
    classDef compute fill:#D86613,stroke:#232F3E,stroke-width:2px,color:white;

    User[👤 End User / Client]:::client

    subgraph Cloudflare Edge
        CF_DNS[🌐 Cloudflare DNS]:::cloudflare
        CF_CDN[⚡ Cloudflare CDN]:::cloudflare
        R2[🪣 Cloudflare R2<br/>Zero-Egress Storage]:::cloudflare
    end

    subgraph AWS Cloud
        ALB[⚖️ Application Load Balancer]:::aws
        ECR[📦 AWS ECR<br/>Docker Registry]:::aws
        
        subgraph AWS ECS Fargate
            Web[🖥️ Django Web Server<br/>Docker Container]:::compute
            Worker[⚙️ Celery Worker<br/>Docker Container]:::compute
            Beat[⏱️ Celery Beat<br/>Docker Container]:::compute
        end
    end

    subgraph Multi-Cloud Data
        DB[(🐘 Database<br/>Neon Postgres / RDS)]:::db
        Redis[(🔴 Upstash Serverless<br/>Redis Broker)]:::db
    end

    %% External Flow
    User -->|Accesses docshift.com| CF_DNS
    CF_DNS -.->|Serves Static Assets| CF_CDN
    CF_DNS -->|Routes App Traffic| ALB
    CF_CDN -.->|Fetches Assets| R2
    
    %% Compute Layer
    ALB -->|Forwards HTTP Requests| Web
    ECR -.->|Pulls Docker Images| Web
    ECR -.->|Pulls Docker Images| Worker
    
    %% Internal Connections
    Web -->|Read/Write Data| DB
    Web -->|Enqueues Job| Redis
    Web -->|Uploads PDF via S3 API| R2
    
    Worker -->|Pulls Job| Redis
    Worker -->|Updates Status| DB
    Worker -->|Downloads & Uploads PDF via S3 API| R2
    
    Beat -->|Schedules Expiry Tasks| Redis
```

### 🧩 Why this Architecture is Perfect

1. **Massive Cost Savings**: By keeping your storage out of AWS (Cloudflare R2) and your queue Serverless (Upstash), you avoid AWS's notorious egress fees and idle server costs.
2. **Containerized Compute (ECS Fargate)**: You aren't paying for idle EC2 servers. Fargate spins up isolated containers for your Web app and Celery workers, scaling based on PDF processing demand.
3. **Seamless Integration**: Your code talks to Cloudflare R2 exactly as if it were AWS S3. No code changes required!
4. **Global Edge Network**: Cloudflare caches your static files globally and blocks bad traffic before it reaches AWS, keeping your compute costs minimal.
