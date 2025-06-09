# Amadeus Project

Bot de música para Discord com suporte a reprodução de áudio do YouTube.

## Requisitos

- Python 3.11 ou superior (recomendado Python 3.11.8)
- FFmpeg
- Bibliotecas Python (instaladas automaticamente via requirements.txt):
  - discord.py[voice] 2.3.2
  - PyNaCl 1.5.0
  - yt-dlp 2024.3.10

## Configuração do FFmpeg

1. Baixe o FFmpeg para Windows:
   - Acesse [https://github.com/BtbN/FFmpeg-Builds/releases](https://github.com/BtbN/FFmpeg-Builds/releases)
   - Baixe o arquivo `ffmpeg-master-latest-win64-gpl-shared.zip`

2. Extraia o arquivo baixado

3. Crie a seguinte estrutura de pastas no projeto:
   ```
   AMADEUS PROJECT/
   ├── src/
   │   └── config/
   │       └── cookies.json
   └── libraries/
       └── ffmpeg/
           └── bin/
               └── ffmpeg.exe
   ```

4. Copie o arquivo `ffmpeg.exe` da pasta `bin` do arquivo extraído para a pasta `libraries/ffmpeg/bin/` do projeto

## Configuração do YouTube

Para evitar bloqueios do YouTube e melhorar a compatibilidade, você tem duas opções:

### Opção 1 (Recomendada) - Usando Cookies
1. Instale a extensão "Get cookies.txt" no Chrome
2. Faça login no YouTube no seu navegador
3. Vá para youtube.com
4. Clique na extensão e exporte os cookies
5. Salve o arquivo como `cookies.json` na pasta `src/config/`

**Importante sobre os cookies:**
- O arquivo `cookies.json` é específico para cada usuário/máquina
- Cada pessoa que for usar o bot precisa gerar seu próprio arquivo
- Os cookies têm validade e podem expirar (geralmente duram alguns meses)
- Se o bot começar a ter problemas de acesso, gere um novo arquivo de cookies
- O arquivo não deve ser compartilhado ou versionado no GitHub
- Mantenha seus cookies seguros, pois eles dão acesso à sua conta do YouTube

**Por que os cookies são necessários?**
- O YouTube implementa medidas anti-bot que podem bloquear o acesso
- Os cookies permitem que o bot acesse o YouTube como um usuário autenticado
- Isso resolve problemas como:
  * "Sign in to confirm you're not a bot"
  * Bloqueios de acesso a certos vídeos
  * Limitações de taxa de requisições
  * Melhor qualidade de áudio disponível

### Opção 2 (Alternativa - Atualmente Aplicada)
- O bot usa configurações otimizadas para streaming
- Evita download de vídeo
- Usa formato de áudio direto
- Pode ter problemas com alguns vídeos
- Pode ser mais lento

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/amadeus-project.git
   cd amadeus-project
   ```

2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   ```

3. Ative o ambiente virtual:
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure o token do bot no arquivo `src/config/config.py`

## Executando o Bot

```bash
python main.py
```

## Comandos Disponíveis

- `/music [nome/url]` - Toca uma música
- `/stop` - Para a música e limpa a fila
- `/pause` - Pausa a música atual
- `/resume` - Retoma a música pausada
- `/skip` - Pula para a próxima música
- `/queue` - Mostra a fila de músicas

## Permissões Necessárias

O bot precisa ter as seguintes permissões no Discord:
- Enviar mensagens
- Gerenciar mensagens
- Conectar-se a canais de voz
- Falar em canais de voz

**Observação**: O usuário que executa os comandos precisa estar em um canal de voz.

## Estrutura do Projeto

```
AMADEUS PROJECT/
├── src/
│   ├── classes/
│   │   ├── __init__.py
│   │   └── music_manager.py
│   ├── config/
│   │   ├── config.py
│   │   └── cookies.json
│   ├── functions.py
│   └── main.py
├── libraries/
│   └── ffmpeg/
│       └── bin/
│           └── ffmpeg.exe
├── requirements.txt
└── README.md
```

## Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes. 

