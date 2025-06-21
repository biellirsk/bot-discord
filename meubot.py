import os
import discord
from discord.ext import commands
import sqlite3
import datetime

# --- 1. Variáveis de Configuração ---
# Substitua 'SEU_TOKEN_AQUI' pelo token real do seu bot
TOKEN = os.getenv('TOKEN') # Seu token
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Manter se você precisa de info de membros

# --- 2. Definição do Objeto Bot ---
# 'bot' DEVE ser definido antes de qualquer @bot.command() ou @bot.event
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. Funções do Banco de Dados ---
def connect_db():
    conn = sqlite3.connect('logs.db')
    return conn

def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS desempenho_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            data TEXT NOT NULL,
            pontuacao INTEGER,
            observacao TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- 4. Eventos do Bot ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name}#{bot.user.discriminator} está online e pronto!')
    await bot.change_presence(activity=discord.Game(name="Registrando Desempenho!"))
    create_table() # Chama a função para criar a tabela do DB quando o bot estiver pronto

# --- 5. Comandos do Bot ---
@bot.command(name='ping', help='Responde com Pong!')
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command(name='hello', help='Diz olá!')
async def hello(ctx):
    await ctx.send(f'Olá, {ctx.author.display_name}!')

@bot.command(name='logar', help='Registra o desempenho de um jogador. Ex: !logar @JogadorX pontuacao:9 Observacao:Jogou muito bem!')
async def logar_desempenho(ctx, membro: discord.Member, *, args):
    user_id = membro.id
    username = membro.display_name
    data = datetime.date.today().strftime("%Y-%m-%d")

    pontuacao = None
    observacao = ""

    # --- INÍCIO DA LÓGICA CORRIGIDA PARA PROCESSAR ARGUMENTOS ---
    # Dividir os argumentos pela palavra-chave "Observacao:" primeiro
    obs_split = args.split("Observacao:", 1)
    
    # A parte antes da observação (pode conter pontuação)
    main_args_str = obs_split[0].strip()
    
    # A parte da observação, se existir
    if len(obs_split) > 1:
        observacao = obs_split[1].strip()

    # Agora, processar a parte principal dos argumentos para pontuação
    main_parts = main_args_str.split()
    for part in main_parts:
        if part.lower().startswith("pontuacao:"):
            try:
                pontuacao = int(part.split(":")[1])
            except ValueError:
                await ctx.send("Pontuação inválida. Use um número inteiro (ex: pontuacao:9).")
                return
    # --- FIM DA LÓGICA CORRIGIDA ---

    if pontuacao is None and not observacao:
        await ctx.send(f"Uso incorreto. Exemplo: `!logar @{ctx.author.display_name} pontuacao:9 Observacao:Jogou muito bem!`")
        return

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO desempenho_logs (user_id, username, data, pontuacao, observacao)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, data, pontuacao, observacao))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="Log de Desempenho Registrado!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Jogador", value=username, inline=True)
    embed.add_field(name="Data", value=data, inline=True)
    if pontuacao is not None:
        embed.add_field(name="Pontuação", value=pontuacao, inline=True)
    if observacao:
        embed.add_field(name="Observação", value=observacao, inline=False)
    embed.set_footer(text=f"Registrado por: {ctx.author.display_name}")

    await ctx.send(embed=embed)


@bot.command(name='ver_logs', help='Mostra os logs de desempenho de um jogador. Ex: !ver_logs @JogadorX [quantidade]')
async def ver_logs(ctx, membro: discord.Member, quantidade: int = 5):
    user_id = membro.id
    username = membro.display_name

    conn = connect_db()
    cursor = conn.cursor()
    # MODIFICADO: Agora seleciona o ID também e removeu 'erros'
    cursor.execute('''
        SELECT id, data, pontuacao, observacao
        FROM desempenho_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    ''', (user_id, quantidade))
    logs = cursor.fetchall()
    conn.close()

    if not logs:
        await ctx.send(f"Nenhum log de desempenho encontrado para {username}.")
        return

    embed = discord.Embed(
        title=f"Logs de Desempenho para {username}",
        description=f"Exibindo os últimos {len(logs)} registros:",
        color=discord.Color.gold()
    )

    for log in reversed(logs):
        # MODIFICADO: Agora extrai o ID também e removeu 'erros'
        log_id, data, pontuacao, observacao = log
        # MODIFICADO: Adiciona o ID na exibição e removeu 'erros'
        log_text = f"**ID:** {log_id}\n**Data:** {data}\n"
        if pontuacao is not None:
            log_text += f"**Pontuação:** {pontuacao}\n"
        if observacao:
            log_text += f"**Obs:** {observacao}\n"
        log_text += "---"

        embed.add_field(name="\u200b", value=log_text, inline=False)

    embed.set_footer(text=f"Solicitado por: {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command(name='apagar_log', help='Apaga um log de desempenho específico. Requer o ID do log. Ex: !apagar_log 123')
@commands.has_permissions(manage_messages=True) # Exemplo: apenas quem pode gerenciar mensagens pode apagar logs
async def apagar_log(ctx, log_id: int):
    """
    Apaga um log de desempenho do banco de dados pelo seu ID.
    Apenas usuários com permissão de 'Gerenciar Mensagens' podem usar este comando.
    """
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM desempenho_logs WHERE id = ?', (log_id,))
    conn.commit()
    rows_deleted = cursor.rowcount # Verifica quantas linhas foram afetadas
    conn.close()

    if rows_deleted > 0:
        embed = discord.Embed(
            title="Log Apagado!",
            description=f"O log com ID `{log_id}` foi removido com sucesso.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Erro ao Apagar Log",
            description=f"Não foi encontrado nenhum log com o ID `{log_id}`.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


# --- 6. Iniciar o Bot ---
bot.run(TOKEN)