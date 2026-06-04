# DocShift Multi-Cloud Architecture (AWS + Cloudflare)

This diagram visualizes how DocShift utilizes AWS for compute and Cloudflare for edge routing and zero-egress file storage.

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
        
        subgraph Elastic Beanstalk / ECS
            Web[🖥️ Django Web Server<br/>Gunicorn]:::compute
            Worker[⚙️ Celery Worker<br/>PDF Processing]:::compute
            Beat[⏱️ Celery Beat<br/>Job Cleanup]:::compute
        end
        
        RDS[(🐘 Amazon RDS<br/>PostgreSQL)]:::db
        Redis[(🔴 ElastiCache<br/>Redis Broker)]:::db
    end

    %% External Flow
    User -->|Accesses docshift.com| CF_DNS
    CF_DNS -.->|Serves Static Assets| CF_CDN
    CF_DNS -->|Routes App Traffic| ALB
    CF_CDN -.->|Fetches Assets| R2
    
    %% Compute Layer
    ALB -->|Forwards HTTP Requests| Web
    
    %% Internal Connections
    Web -->|Read/Write Data| RDS
    Web -->|Enqueues Job| Redis
    Web -->|Uploads PDF via S3 API| R2
    
    Worker -->|Pulls Job| Redis
    Worker -->|Updates Status| RDS
    Worker -->|Downloads & Uploads PDF via S3 API| R2
    
    Beat -->|Schedules Expiry Tasks| Redis
```

### 🧩 Why this Architecture is Perfect

1. **Massive Cost Savings**: By keeping your storage out of AWS, you avoid AWS's notorious `$0.09/GB` data transfer fees. Cloudflare R2 does not charge for egress bandwidth when users download converted PDFs.
2. **Seamless Integration**: Because your code (`settings.py`) sets `AWS_S3_REGION_NAME = 'auto'`, the `django-storages` library talks to Cloudflare R2 exactly as if it were AWS S3. No code changes required!
3. **AWS Compute Power**: You still get the reliability and auto-scaling power of AWS Elastic Beanstalk / ECS for running the CPU-heavy PDF processing tasks. 
4. **Global Edge Network**: Cloudflare caches your static files globally, taking the load off your web server.
