# Docker Setup - Proposta FastAPI

Este projeto inclui configurações Docker para facilitar o deploy em servidores Linux.

## Arquivos Docker

- `Dockerfile` - Configuração da imagem Docker da aplicação
- `docker-compose.yml` - Configuração básica para desenvolvimento/teste
- `.dockerignore` - Arquivos ignorados durante o build
- `nginx.conf` - Configuração do Nginx como reverse proxy

## Como usar

### Desenvolvimento/Teste

```bash
# Build e start da aplicação
docker-compose up --build

# Em background
docker-compose up -d --build

# Parar os serviços
docker-compose down
```

## Configurações

### Portas
- **5001**: API FastAPI (mapeada para evitar conflito com outros projetos)
- **8080**: Nginx (se habilitado com reverse proxy)

### Volumes
- `./media` - Arquivos de mídia gerados
- `./propostas` - PDFs das propostas geradas
- `./fonts` - Fontes utilizadas nos PDFs
- `./img` - Imagens utilizadas
- `./webhook.log` - Log da aplicação

### Variáveis de Ambiente
- `PYTHONUNBUFFERED=1` - Output imediato do Python

## Monitoramento

### Health Check
A aplicação inclui health check que verifica se está respondendo na porta 8000 (interna do container).

### Logs
```bash
# Ver logs da aplicação
docker-compose logs -f proposta-api
```

## Segurança

- Aplicação roda com usuário não-root
- Logs estruturados

## Comandos Úteis

```bash
# Rebuild apenas a aplicação
docker-compose build proposta-api

# Executar comando dentro do container
docker-compose exec proposta-api bash

# Ver status dos containers
docker-compose ps

# Limpar volumes não utilizados
docker volume prune

# Limpar imagens não utilizadas
docker image prune
```

## Integração com Nginx existente

Para integrar com seu Nginx existente que já gerencia outros projetos, adicione esta configuração ao seu arquivo de configuração do Nginx:

```nginx
# Configuração para api.energiaa.com.br
server {
    listen 80;
    server_name api.energiaa.com.br;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.energiaa.com.br;
    charset utf-8;
    
    # Seus certificados SSL
    ssl_certificate /etc/letsencrypt/live/api.energiaa.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.energiaa.com.br/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 75M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Servir arquivos de mídia diretamente
    location /media/ {
        alias /caminho/para/seu/projeto/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        access_log off;
    }
}
```

## Troubleshooting

### Problemas de Permissão
Se houver problemas de permissão com volumes:
```bash
sudo chown -R 1000:1000 ./media ./propostas
```

### Verificar se a aplicação está funcionando
```bash
curl http://localhost:8001/
```

### Logs detalhados
```bash
docker-compose logs --tail=100 -f proposta-api
```