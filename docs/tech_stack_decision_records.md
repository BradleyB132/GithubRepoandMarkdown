# Technology Stack Decision: .NET MVC with SQLite

## Status
Proposed

## Context
The campus events system is an internal university application with low to moderate usage, a small development team, and limited operational budget. The system must support event submission, review workflows, and event discovery while remaining easy to maintain and extend over multiple semesters.

The development team is expected to be more familiar with traditional MVC patterns than distributed systems, and the project does not require real-time processing, high availability, or horizontal scalability.

The selected technology stack should:
- Support rapid development with strong tooling
- Be easy to maintain by a small team
- Require minimal infrastructure and operational overhead
- Align with a layered, modular monolith architecture

---

## Decision
The system will be built using the following technology stack:

- **Backend Framework:** ASP.NET Core MVC (C#)
- **Data Access:** Entity Framework Core (Code First)
- **Database:** SQLite
- **Frontend Rendering:** Razor Views (server-side rendering)
- **Authentication:** ASP.NET Core Identity (basic role separation only)
- **Hosting:** Cloud-hosted VM or App Service (e.g., Azure App Service)

---

## Alternatives Considered

### Java Spring Boot with PostgreSQL
This option provides strong scalability and enterprise-grade features but was not selected due to increased configuration complexity, steeper learning curve, and higher operational overhead for a small team.

### Node.js with Express and MongoDB
While flexible and lightweight, this stack lacks the strong typing, structured MVC patterns, and integrated tooling provided by ASP.NET Core, making long-term maintainability more difficult for this project.

### ASP.NET Core with SQL Server
SQL Server offers advanced features but was not chosen due to licensing considerations and unnecessary complexity for the expected workload. SQLite sufficiently meets performance and data persistence requirements.

---

## Consequences

### Positive
- Strong alignment with MVC and layered architecture principles
- Excellent tooling support via Visual Studio and .NET CLI
- Minimal infrastructure and operational costs
- Easy local development and deployment
- Simple database setup with zero external dependencies
- Straightforward onboarding for new developers

### Negative
- SQLite has limited concurrency support compared to full-scale RDBMSs
- Not suitable for very high traffic or heavy write workloads
- Future migration to a different database may require schema adjustments
- Less flexibility for horizontal scaling
