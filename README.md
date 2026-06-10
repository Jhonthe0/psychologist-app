# PsiLine

Sistema Django para gerenciamento de atendimentos psicologicos remotos em uma clinica escola.

O projeto entrega uma API REST protegida por JWT, um Django Admin para operacao interna e telas HTML feitas com templates Django para apresentar uma interface inicial com aparencia clinica/hospitalar.

## Funcionalidades

- Docker com Django e PostgreSQL.
- Django Admin protegido por usuario e senha.
- API REST com autenticacao JWT.
- Front-end Django com home, tela de entrada, painel clinico, listagens e agenda.
- Cadastro de usuarios com papel `admin`, `trainee` ou `patient`.
- Cadastro e gerenciamento de pacientes.
- Cadastro e gerenciamento de estagiarios.
- Cadastro, listagem e cancelamento de consultas.
- Relatorios por estagiario, paciente e periodo.
- Agenda do estagiario com atualizacao do link da reuniao.

## Stack

- Python 3.12
- Django 5
- Django REST Framework
- Simple JWT
- PostgreSQL 16
- Docker Compose
- HTML e CSS com templates Django

## Como subir o projeto

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Suba os containers:

```bash
docker compose up --build
```

Se sua instalacao usar o Compose antigo, rode:

```bash
docker-compose up --build
```

O container executa as migrations automaticamente ao iniciar.

## Acessos principais

Front-end publico:

```text
http://localhost:8000/
```

Tela de entrada:

```text
http://localhost:8000/login/
```

Painel clinico:

```text
http://localhost:8000/app/
```

Agenda do estagiario:

```text
http://localhost:8000/app/agenda/
```

Django Admin:

```text
http://localhost:8000/admin/
```

API:

```text
http://localhost:8000/api/
```

## Criar administrador

Em outro terminal, com os containers rodando:

```bash
docker compose exec web python manage.py createsuperuser
```

Ou, se estiver usando o Compose antigo:

```bash
docker-compose exec web python manage.py createsuperuser
```

O superusuario recebe automaticamente o papel `admin`.

## Criar admin de desenvolvimento rapidamente

Opcionalmente, crie um usuario admin padrao para testes:

```bash
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); user, created=User.objects.get_or_create(username='admin', defaults={'email':'admin@example.com'}); user.email='admin@example.com'; user.is_staff=True; user.is_superuser=True; user.is_active=True; user.role='admin'; user.set_password('Admin123!'); user.save(); print('created' if created else 'updated')"
```

Acesso:

```text
Usuario: admin
Senha: Admin123!
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

Paciente atendido no sistema.

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

## Regras de negocio

- Nao agenda consulta para paciente inativo.
- Nao agenda consulta para estagiario inativo.
- Nao permite duas consultas agendadas para o mesmo estagiario no mesmo horario.
- Exclusao de paciente e estagiario e logica, usando `active=false`.
- Nao inativa paciente ou estagiario com consulta futura agendada.
- Cancelamento de consulta altera o status para `canceled`.

## Telas do front-end

```text
GET /              Home publica
GET /login/        Tela visual de entrada
GET /app/          Painel clinico administrativo
GET /app/patients/ Pacientes
GET /app/trainees/ Estagiarios
GET /app/appointments/ Consultas
GET /app/agenda/   Agenda do estagiario
```

Nesta primeira entrega, as paginas visuais de `/app/` ficam publicas para demonstracao do sistema sem login. O Django Admin e a API protegida continuam exigindo autenticacao.

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

Use `?include_inactive=true` para listar registros inativos.

### Estagiarios

```text
GET    /api/admin/trainees/
POST   /api/admin/trainees/
GET    /api/admin/trainees/{id}/
PUT    /api/admin/trainees/{id}/
PATCH  /api/admin/trainees/{id}/
DELETE /api/admin/trainees/{id}/
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

### Relatorios

```text
GET /api/admin/reports/by-trainee/?trainee_id=1
GET /api/admin/reports/by-patient/?patient_id=1
GET /api/admin/reports/by-period/?start_date=2026-05-01T00:00:00-03:00&end_date=2026-05-31T23:59:59-03:00
```

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

Copie `.env.example` para `.env` e ajuste se necessario:

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

## Testes

Rodar testes dentro do container:

```bash
docker compose exec web python manage.py test
```

Ou:

```bash
docker-compose exec web python manage.py test
```

## Dados demo

Para popular o banco com pacientes, estagiarios e consultas suficientes para testar agenda e relatorios:

```bash
docker compose exec web python manage.py seed_demo_data
```

O comando e idempotente: pode rodar mais de uma vez sem duplicar os registros demo.

Para limpar apenas os dados demo conhecidos e recriar:

```bash
docker compose exec web python manage.py seed_demo_data --reset-demo
```

Ele cria:

- 12 pacientes demo com data de nascimento.
- 5 estagiarios demo com supervisor.
- 60 consultas distribuidas entre `scheduled`, `completed` e `canceled`.
- Motivos de cancelamento em consultas canceladas.

Senha dos estagiarios demo:

```text
Demo123456
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
