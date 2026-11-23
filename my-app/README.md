# Лаборатория диагностики VPS

Учебный стенд для DevOps-практики: запускает ограниченную нагрузку на CPU/RAM/диск/HTTP, показывает метрики в реальном времени и позволяет специально включать задержки, ошибки и деградацию readiness.

## Быстрый запуск через Docker

Требования: Linux/macOS, Docker Engine и Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

По умолчанию Compose слушает только `127.0.0.1:8080` на VPS. Подключайтесь через SSH-туннель:

```bash
ssh -N -L 8080:127.0.0.1:8080 user@SERVER_IP
```

После этого откройте `http://127.0.0.1:8080` на своём компьютере. Если нужен прямой доступ из закрытой сети, задайте `FRONTEND_BIND=0.0.0.0` в `.env` и ограничьте TCP/8080 списком разрешённых адресов в firewall. Backend доступен frontend-контейнеру внутри Docker-сети, а healthcheck не даёт frontend стартовать раньше API.

Остановка и просмотр логов:

```bash
docker compose logs -f backend
docker compose down
```

## Локальная разработка без Docker

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload --port 8000
```

В другом терминале:

```bash
cd frontend
npm install
npm run dev
```

Откройте `http://localhost:5173`. Vite проксирует `/api` и `/metrics` на `localhost:8000`.

## Что можно тренировать

- **Нагрузка на CPU:** количество процессов и интенсивность → рост CPU/load average.
- **Нагрузка на память:** ограниченное выделение памяти → изменение memory percent и available memory.
- **Дисковый ввод-вывод:** временная запись до 256 МиБ → disk usage и write bytes.
- **Параллельные HTTP-запросы:** до 50 внутренних запросов → latency и API request rate.
- **Медленный API:** задержка до 5 секунд → latency и устаревшая телеметрия.
- **Шквал ошибок:** error rate до 100% → ошибки API и readiness.
- **Восстановление:** остановите задания, сбросьте fault toggles и проверьте возврат health/readiness.

Сначала запускайте одно небольшое задание, фиксируйте симптом, формулируйте гипотезу и только затем увеличивайте нагрузку. Одновременно разрешены максимум два задания.

## API и Prometheus

```bash
curl http://127.0.0.1:8080/api/healthz
curl http://127.0.0.1:8080/api/readiness
curl http://127.0.0.1:8080/metrics
curl http://127.0.0.1:8080/api/load/jobs
curl -X POST http://127.0.0.1:8080/api/load/jobs \
  -H 'content-type: application/json' \
  -d '{"kind":"cpu","duration_seconds":30,"intensity":0.5,"workers":1}'
```

`/metrics` отдаёт текстовый формат, совместимый с Prometheus. На следующем этапе к нему можно подключить Prometheus/Grafana или заменить sampler на node-exporter для наблюдения всего VPS.

## Безопасное размещение на VPS

Это учебный стенд без аутентификации. Не публикуйте его в интернет без SSH-туннеля, VPN или списка разрешённых адресов в firewall. Минимальный безопасный вариант — разрешить входящий TCP/8080 только со своего IP и закрыть порт после занятия.

По умолчанию метрики относятся к backend-контейнеру. Это безопаснее и предсказуемее. Для отдельного Linux-эксперимента с метриками пространства имён хоста можно сделать override Compose с `pid: host`, но это расширяет видимость процессов и должно выполняться только на одноразовом учебном VPS; в базовый compose этот режим намеренно не включён.

## Сценарий диагностики

Подробный чек-лист находится в [`docs/troubleshooting-checklist.md`](docs/troubleshooting-checklist.md). Начинайте с `docker compose ps`, health-endpoint'ов и логов, затем сопоставляйте графики с `docker stats`, `top`, `free -h`, `df -h` и `ss -s`.

