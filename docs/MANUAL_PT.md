# NeoCraft Macro Desk — Manual do Usuário

Um macro pad personalizado: uma grade de 16 botões (4×4) mais 3 encoders
rotativos, junto com um aplicativo de desktop para Windows que decide o que
cada botão e encoder faz.

---

## Parte 1 — O que ele faz

### O hardware
- **16 botões** organizados em uma grade 4×4. 15 deles (`BTN0`–`BTN14`)
  executam ações que você define. O 16º, **`2FX`**, não é um botão de ação —
  é uma tecla de troca de camada (veja abaixo).
- **3 encoders rotativos** (`ENC1`–`ENC3`). Girar ajusta um volume; clicar
  (apertar) muta/desmuta. *No momento, apenas o ENC1 está ativo no
  firmware — ENC2 e ENC3 estão fisicamente presentes, mas ainda não
  funcionam.*
- **LEDs endereçáveis**, um por tecla, mostrando um padrão de cor animado
  enquanto tudo está conectado, ou **vermelho sólido** se o aplicativo não
  estiver rodando/conectado — um lembrete visual embutido para abrir o app.

### O aplicativo
Um programinha que fica na bandeja do sistema (system tray). Ele conversa
com o pad via USB e permite atribuir uma ação a cada botão, e um alvo de
volume a cada encoder. Cada botão pode fazer uma destas ações:

| Tipo de ação | O que faz |
|---|---|
| **Teclado** | Envia uma combinação de teclas (ex.: `ctrl+c`) para o app que estiver em foco |
| **Macro** | Igual ao Teclado, mas você grava a combinação apertando-a de verdade, em vez de digitar |
| **Cena OBS** | Troca a cena do OBS Studio para uma cena específica (requer o OBS rodando com o servidor WebSocket ligado) |
| **Som** | Toca um arquivo de áudio (WAV, MP3, OGG, FLAC, AIFF) — com controles de volume e corte |
| **Vazio** | Não faz nada (estado padrão do botão) |

Cada encoder pode controlar o **volume geral do sistema**, ou o volume de
**um aplicativo específico** (mesmo apps com várias janelas, como um
navegador) — você escolhe, por encoder.

### A segunda camada "2FX"
Todo botão pode ter **duas ações diferentes** — uma normal (Camada 1) e uma
segunda (Camada 2) que só dispara quando você arma deliberadamente:

1. Toque em **`2FX`** — a borda do app pisca vermelho, a Camada 2 fica
   armada.
2. Toque em qualquer outro botão — ele executa *a ação da Camada 2 daquele
   botão*, e o pad volta automaticamente para a Camada 1.
3. Se você não apertar nada, a Camada 2 se desarma sozinha depois de um
   tempo (10 segundos por padrão, ajustável até 60s).
4. Tocar em **`2FX`** de novo enquanto está armado cancela manualmente, sem
   executar nenhuma ação.

É assim que um pad de 16 teclas te dá, na prática, 30 ações configuráveis.

### Funcionamento em segundo plano
Fechar a janela do app (o botão **X**) não encerra o programa — ele
minimiza para a bandeja do sistema e continua rodando, então seus mapeamentos
de botões/encoders continuam ativos. Use a opção **Sair** no menu da bandeja
para encerrar de verdade.

### Idioma
O aplicativo está disponível em **Português** e **English**, trocável a
qualquer momento em Configurações (veja
[Trocando o idioma do aplicativo](#trocando-o-idioma-do-aplicativo)).
O padrão é Português. *Nota: as capturas de tela deste manual foram feitas
antes desse recurso existir, então alguns rótulos mostrados (títulos de
janela, texto de botão) estão no idioma que era padrão na época — o layout
e o fluxo das janelas são idênticos, só o texto muda conforme o idioma
agora.*

---

## Parte 2 — Instalação

1. Baixe o `NeoCraft-Macro-Desk-Setup.exe`.
2. Dê duplo clique nele. **Nenhuma solicitação de administrador vai
   aparecer** — a instalação é só para a sua conta do Windows, não para o
   sistema todo.
3. Opcionalmente marque **"Create a desktop shortcut"** no assistente.
4. Avance até o fim. O instalador cria uma entrada no Menu Iniciar
   (**NeoCraft Macro Desk**) e um desinstalador.
5. Conecte o macro pad via USB.
6. Abra o aplicativo (Menu Iniciar, ou o atalho na área de trabalho, se
   você criou um).

O aplicativo conecta automaticamente — sem tela de configuração, sem
drivers para instalar separadamente (o driver USB-serial embutido do
Windows já cuida do Pro Micro). Ele encontra o pad pela identidade USB
dele, não por um número fixo de porta COM, então conecta corretamente
não importa em qual porta COM o Windows o coloque (o que pode mudar se
você plugar em uma porta USB diferente).

**Se os LEDs ficarem vermelho sólido depois de abrir o app:** o aplicativo
não está enxergando o pad de jeito nenhum — confira o cabo/conexão USB, e
confirme que ele aparece no Gerenciador de Dispositivos do Windows, em
Portas (COM & LPT).

**Para desinstalar:** Menu Iniciar → NeoCraft Macro Desk → "Uninstall
NeoCraft Macro Desk", ou Configurações do Windows → Aplicativos. Sua
configuração salva de botões/encoders é mantida (caso você reinstale
depois) — veja
[Onde suas configurações ficam salvas](#onde-suas-configurações-ficam-salvas)
se quiser removê-la manualmente também.

---

## Parte 3 — Como usar cada função

### A janela principal

![Janela principal](images/main_window.png)

*Nota: esta captura de tela é de antes de uma pequena mudança de layout —
o único botão embaixo agora são três, lado a lado: **Configurações de
Cor**, **Configurações** e **Ajuda** (veja abaixo).*

Uma grade 4×4 de botões, mais os 3 encoders à direita. A borda animada
mostra o padrão de LED atual do pad, ao vivo. Clique em **qualquer botão**
para configurá-lo. Abaixo da grade, três botões:
- **Configurações de Cor** — muda o padrão de LED (veja
  [Mudando o padrão de LED](#mudando-o-padrão-de-led)).
- **Configurações** — tempo da 2FX e idioma do app (veja
  [Trocando o idioma do aplicativo](#trocando-o-idioma-do-aplicativo)).
- **Ajuda** — versão do app e links para este manual e para o repositório
  no GitHub (veja [Ajuda](#ajuda)).

### Atribuindo um atalho de teclado ou macro a um botão

1. Clique no botão que quer configurar (ex.: `BTN0`).
2. Escolha a **Camada** (Camada 1 = normal, Camada 2 (2FX) = segunda
   função).
3. Defina o **Tipo de ação** como **Teclado** ou **Macro**.
   - **Teclado**: digite a combinação diretamente, ex.: `ctrl+c`.
   - **Macro**: clique no campo e aperte a combinação de verdade no seu
     teclado — ela é capturada ao vivo.
4. Clique em **OK** para salvar.

![Configuração de macro](images/config_macro.png)

### Atribuindo um som a um botão

1. Clique no botão, defina o **Tipo de ação** como **Som**.
2. Clique em **Procurar...** e escolha um arquivo de áudio (WAV, MP3, OGG,
   FLAC ou AIFF).
3. Ajuste o **Volume** com o controle deslizante (0–100%).
4. Arraste as duas alças em **Corte** para tocar só parte do clipe — o
   texto abaixo mostra o início/fim selecionado e a duração total.
5. Use **▶ Testar som** / **■ Parar** para conferir se está do jeito certo
   antes de salvar.
6. Clique em **OK**.

![Configuração de som](images/config_sound.png)

### Atribuindo uma troca de cena do OBS

1. Clique no botão, defina o **Tipo de ação** como **Cena OBS**.
2. Digite o nome exato da cena como aparece no OBS.
3. Clique em **OK**.

Isso requer o OBS Studio rodando com o servidor WebSocket habilitado (o
OBS 28+ já vem com isso — Tools → WebSocket Server Settings).

### Limpando um botão

Defina o **Tipo de ação** como **Vazio** e clique em **OK**.

### Usando a segunda camada 2FX

Toque na tecla **`2FX`** do pad (canto inferior direito da grade). A borda
do app pisca vermelho enquanto está armada. O próximo botão que você
apertar executa sua ação da **Camada 2** em vez da Camada 1, e o pad volta
ao normal automaticamente. Toque em `2FX` de novo antes de apertar outra
coisa para cancelar sem executar nenhuma ação.

Para mudar quanto tempo a Camada 2 fica armada antes de desarmar sozinha,
clique no botão **Configurações** abaixo da grade:

![Janela de Configurações](images/config_2fx_timeout.png)

### Trocando o idioma do aplicativo

Abra a mesma janela de **Configurações** e use o menu **Idioma** /
**Language** na parte de baixo — escolha **Português** ou **English** e
clique em **OK**. A mudança é aplicada na hora: qualquer janela que você
abrir em seguida (configurar botão, configurar encoder, configurações de
cor) já aparece no novo idioma, sem precisar reiniciar. Os botões
**Configurações de Cor**/**Configurações**/**Ajuda** e os textos **Abrir**/
**Sair** do menu da bandeja também atualizam na hora.

### Ajuda

Clique no botão **Ajuda** abaixo da grade para ver o número da versão do
app e dois links — um para este manual no GitHub, outro para o repositório
do projeto. Os dois abrem no seu navegador padrão.

### Configurando um encoder

1. Clique em um encoder (`ENC1`, `ENC2` ou `ENC3`) na janela do app.
2. Escolha o modo:
   - **Volume Geral** (**System Volume** em inglês) — controla o volume
     geral do Windows.
   - **Aplicativo** (**Application**) — controla o volume de um app
     específico, independentemente (clique em **Selecionar...** e escolha
     o `.exe`). Funciona corretamente até com apps que rodam como vários
     processos ao mesmo tempo, como navegadores baseados em Chromium.
3. Clique em **OK**.

![Configuração de encoder](images/config_encoder.png)

Depois de configurado: **gire** o encoder para ajustar o volume,
**clique** nele (aperte para baixo) para mutar/desmutar.

### Mudando o padrão de LED

Clique em **Configurações de Cor** na parte de baixo da janela principal.

![Configurações de cor](images/config_color.png)

- **Padrão**: Cor Sólida, Respiração, Onda Arco-íris ou Ciclo de Cor.
- **Cor**: escolha uma cor na roda — usada apenas por Cor Sólida e
  Respiração (fica desabilitada nos outros modos, já que Onda Arco-íris e
  Ciclo de Cor geram suas próprias cores).
- **Brilho** / **Velocidade**: controles deslizantes, aplicados na hora e
  salvos junto com o resto das suas configurações.

### O ícone na bandeja do sistema

![Menu da bandeja](images/tray_menu.png)

Clique com o botão direito (ou, em alguns sistemas, o esquerdo) no ícone da
bandeja para:
- **Abrir** — traz a janela principal de volta.
- **Sair** — encerra o app de verdade (os mapeamentos de botões/encoders
  param de funcionar até você reabrir, e os LEDs do pad ficam vermelho
  sólido).

### Onde suas configurações ficam salvas

Seus mapeamentos de botões, alvos de encoder e configurações de cor ficam
guardados em:

```
%APPDATA%\NeoCraft Macro Desk\config.json
```

Esse arquivo permanece entre atualizações e reinstalações do app. Apagá-lo
reseta tudo para o padrão na próxima vez que o app abrir.
