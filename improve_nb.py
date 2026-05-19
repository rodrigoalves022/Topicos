import json
from pathlib import Path

nb_path = Path(r'c:\Users\rodrigo.silva\Pictures\UFG\DB FIN\analise_gap_win.ipynb')

with open(nb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Remover cell 3 (porque o código dele é apenas o `data_table.enable()`)
# Vou checar se a cell 3 é exatamente aquilo.
for i, c in enumerate(nb['cells']):
    src = ''.join(c['source'])
    if 'data_table.enable_dataframe_formatter()' in src:
        # Se for SÓ isso (menos de 6 linhas úteis), removo a cell inteira. Se tiver mais coisas, removo só essa parte.
        linhas = [l for l in c['source'] if not ('google.colab' in l or 'data_table' in l)]
        if not any(l.strip() and not l.strip().startswith('#') for l in linhas):
            # Célula vazia, deletar
            idx_del = i
            break
        else:
            # Mantém o resto
            c['source'] = linhas
            idx_del = -1
            break

if idx_del >= 0:
    nb['cells'].pop(idx_del)

# Agora vamos na celular de exportação (exportacoes = {...)
for c in nb['cells']:
    src = ''.join(c['source'])
    if 'exportacoes = {' in src:
        # Add markdown export loop
        md_export_code = """
# ── EXPORTAÇÃO MARKDOWN PARA COPILOT ──
# Ferramentas de IA leem Markdown muito melhor do que CSV/HTML.
try:
    for nome, df in [
        ('contagem_gaps_resumo', contagem_gaps),
        ('tabela_gap_alta_apresentacao', tabela_gap_alta_apresentacao),
        ('tabela_gap_baixa_apresentacao', tabela_gap_baixa_apresentacao)
    ]:
        caminho_md = PASTA_SAIDA / f'{nome}.md'
        df.to_markdown(caminho_md, index=False)
    print('Tabelas de apresentação convertidas para .md com sucesso!')
except Exception as e:
    print('Avise no código que a lib tabulate é necessária para exportar raw markdown se falhar')
"""
        if '# ── EXPORTAÇÃO MARKDOWN PARA COPILOT ──' not in src:
            src += md_export_code
            c['source'] = src.splitlines(keepends=True)
        break


with open(nb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print('Modificado com sucesso')
