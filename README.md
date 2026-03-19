# Wallpaper Switcher

Troca automaticamente o wallpaper do **Wallpaper Engine** conforme o aplicativo em execução.

## Requisitos

- Windows 10/11
- Python 3.9+
- Wallpaper Engine instalado via Steam

## Instalação

```bat
pip install -r requirements.txt
python app.py
```

## Como usar

1. **Wallpaper Engine** — confirme ou ajuste o caminho do `wallpaper32.exe`
2. **Mapeamentos** — adicione entradas no formato:
   - **Processo:** nome do `.exe` (ex.: `P5R.exe`)
   - **Caminho:** string completa para o `project.json` do workshop (ex.: `C:\Program Files (x86)\Steam\steamapps\workshop\content\431960\2062717574\project.json`)
3. Clique em **Salvar configuração** para persistir as alterações
4. Clique em **Iniciar monitoramento** — o app verifica a cada 10 segundos quais processos estão rodando

## Configuração persistente

As configurações ficam salvas em `%USERPROFILE%\.wallpaper_switcher_config.json`.
