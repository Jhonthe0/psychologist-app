# PsiLine API

Backend Django para gerenciamento de atendimentos psicologicos remotos do projeto PsiLine.

Nesta etapa o projeto entrega:

- Docker com Django e PostgreSQL.
- Django Admin protegido por login e senha.
- API protegida por JWT.
- Tabelas principais: usuarios, pacientes, estagiarios e consultas.
- Endpoints administrativos para pacientes, estagiarios, consultas e relatorios.
- Endpoints iniciais do ambiente do estagiario para agenda e atualizacao do link da reuniao.

## Stack

- Python 3.12
- Django 5
- Django REST Framework
- Simple JWT
- PostgreSQL 16
- Docker Compose

## Como subir o projeto

```bash
docker compose up --build
```

A API ficara disponivel em:

```text
http://localhost:8000
```

O container executa as migrations automaticamente ao iniciar.

## Criar administrador

Em outro terminal:

```bash
docker compose exec web python manage.py createsuperuser
```

O superusuario tambem recebe o papel `admin` automaticamente.

## Acessos

Django Admin:

```text
http://localhost:8000/admin/
```

API:

```text
http://localhost:8000/api/
```

## Autenticacao JWT

Gerar token:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"sua-senha"}'
```

Usar o token:

```bash
curl http://localhost:8000/api/admin/patients/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN"
```

Renovar token:

```text
POST /api/auth/token/refresh/
```

## Modelo de dados

### User

Usuario base de autenticacao do Django.

Campos principais:

- `username`
- `email`
- `password`
- `role`: `admin`, `trainee` ou `patient`
- `is_active`
- `is_staff`
- `is_superuser`

### Patient

Paciente atendido no sistema. Na primeira versao do requisito, o paciente nao acessa diretamente o sistema, mas o relacionamento opcional com `User` ja permite evoluir para login de paciente depois.

Campos principais:

- `user` opcional
- `name`
- `cpf`
- `email`
- `phone`
- `active`
- `created_at`
- `updated_at`

### Trainee

Estagiario que realiza atendimentos. Cada estagiario possui um `User` para login.

Campos principais:

- `user`
- `registration_number`
- `phone`
- `active`
- `created_at`
- `updated_at`

### Appointment

Consulta entre paciente e estagiario.

Campos principais:

- `trainee`
- `patient`
- `scheduled_at`
- `call_link`
- `status`: `scheduled`, `completed` ou `canceled`
- `active`
- `created_at`
- `updated_at`

Regras implementadas:

- Nao agenda consulta para paciente inativo.
- Nao agenda consulta para estagiario inativo.
- Nao permite duas consultas agendadas para o mesmo estagiario no mesmo horario.
- Exclusao de paciente e estagiario e logica (`active=false`).
- Nao inativa paciente ou estagiario com consulta futura agendada.
- Cancelamento de consulta altera status para `canceled` e remove da listagem padrao.

## Endpoints administrativos

Todos os endpoints abaixo exigem JWT de usuario com papel `admin` ou `is_staff=true`.

### Pacientes

```text
GET    /api/admin/patients/
POST   /api/admin/patients/
GET    /api/admin/patients/{id}/
PUT    /api/admin/patients/{id}/
PATCH  /api/admin/patients/{id}/
DELETE /api/admin/patients/{id}/
```

Exemplo de cadastro:

```json
{
  "name": "Maria Silva",
  "cpf": "12345678900",
  "email": "maria@example.com",
  "phone": "35999999999"
}
```

Use `?include_inactive=true` para listar tambem registros inativos.

### Estagiarios

```text
GET    /api/admin/trainees/
POST   /api/admin/trainees/
GET    /api/admin/trainees/{id}/
PUT    /api/admin/trainees/{id}/
PATCH  /api/admin/trainees/{id}/
DELETE /api/admin/trainees/{id}/
```

Exemplo de cadastro:

```json
{
  "name": "Joao Pereira",
  "email": "joao@example.com",
  "registration_number": "20250001",
  "phone": "35988888888",
  "password": "SenhaForte123"
}
```

O login do estagiario usa a matricula como `username`.

### Consultas

```text
GET    /api/admin/appointments/
POST   /api/admin/appointments/
GET    /api/admin/appointments/{id}/
PUT    /api/admin/appointments/{id}/
PATCH  /api/admin/appointments/{id}/
DELETE /api/admin/appointments/{id}/
POST   /api/admin/appointments/{id}/cancel/
```

Exemplo de agendamento:

```json
{
  "trainee": 1,
  "patient": 1,
  "scheduled_at": "2026-05-20T14:00:00-03:00",
  "call_link": "https://meet.example.com/abc",
  "status": "scheduled"
}
```

### Relatorios

```text
GET /api/admin/reports/by-trainee/?trainee_id=1
GET /api/admin/reports/by-patient/?patient_id=1
GET /api/admin/reports/by-period/?start_date=2026-05-01T00:00:00-03:00&end_date=2026-05-31T23:59:59-03:00
```

Os relatorios retornam JSON com as consultas encontradas. Exportacao PDF/CSV ficou preparada como evolucao futura, pois neste momento o pedido foi para tabelas e endpoints.

## Endpoints do estagiario

Exigem JWT de usuario com papel `trainee`.

```text
GET   /api/trainee/agenda/
GET   /api/trainee/agenda/{id}/
PATCH /api/trainee/agenda/{id}/meeting-link/
```

Atualizar link da reuniao:

```json
{
  "call_link": "https://meet.example.com/sala-atualizada"
}
```

## Variaveis de ambiente

O projeto ja inclui `.env` para desenvolvimento local. Para outro ambiente, copie `.env.example` e ajuste:

```text
DEBUG
SECRET_KEY
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
```

## Comandos uteis

Rodar migrations:

```bash
docker compose exec web python manage.py migrate
```

Criar nova migration:

```bash
docker compose exec web python manage.py makemigrations
```

Shell Django:

```bash
docker compose exec web python manage.py shell
```

Parar containers:

```bash
docker compose stop
```
