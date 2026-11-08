# Resume Project Summary

## Chinese Resume Version

```text
Campus Parcel Station｜校园快递驿站管理系统（Python / Flask / SQLite）

• 独立完成 B/S 架构校园快递驿站管理系统，使用 Flask 构建网页与业务路由，
  使用 SQLite 完成工作人员、包裹及操作日志持久化，覆盖入库、查询、取件与报表闭环。
• 采用分层结构拆分认证、页面路由、包裹服务、统计服务与数据访问；使用 Package、
  Station 业务模型及字典、二维货架状态组织包裹和货位数据。
• 实现自动货位分配、唯一四位取件码、超期费用计算、货位释放、状态筛选及按取件码、
  收件人、快递公司搜索，并使用事务保证入库、取件和审计记录的一致性。
• 基于 Flask Session、PBKDF2 密码哈希和 CSRF Token 实现工作人员登录与后台访问控制；
  增加 CSP、X-Frame-Options、no-store 等安全响应头。
• 编写并执行 32 项自动化测试，覆盖认证、CSRF、收费边界、货位满载与回收、
  取件流程、空数据状态、错误页面和安全响应头，全部通过。
```

## English Resume Version

```text
Campus Parcel Station | Python, Flask, SQLite

- Built a full-stack campus parcel management system covering staff authentication,
  parcel check-in, live search, pickup confirmation, overdue-fee calculation,
  shelf release, audit history, and operational reporting.
- Designed layered modules for routes, authentication, business services, reporting,
  and SQLite persistence; modeled parcels, staff accounts, operation logs, and
  a 4-by-5 shelf resource map.
- Implemented transactional check-in and pickup workflows with unique pickup codes,
  automatic shelf allocation, database constraints, validation, and domain errors.
- Secured staff pages with hashed passwords, server-side sessions, CSRF tokens,
  protected routes, and browser security headers.
- Added 32 automated tests covering authentication, fee boundaries, shelf capacity,
  parcel workflows, reports, error handling, and security behaviour.
```

## Claims to Avoid

Do not describe the project as:

- Production-ready
- High-concurrency
- Enterprise-grade
- AI-powered
- A real university deployment

Use accurate phrases such as:

- Portfolio-grade full-stack MVP
- Locally runnable management system
- Transactional SQLite workflow
- Tested Flask application
