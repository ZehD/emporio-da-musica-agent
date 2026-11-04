# Expired promotion, Black Friday and an out-of-stock item

> **What this shows:** The Takamine GD20 (a sample question from the brief) has an expired 12% promotion. The manual says Black Friday is in November, but no Black Friday promotion is active in the data. The agent quotes the current price and doesn't promise any discount. Then the customer asks for an item that's out of stock, and the agent offers in-stock alternatives.
>
> Model: `anthropic/claude-haiku-5.5` · Store date: 2026-11-03 · Recorded from a real run (`python -m scripts.record_conversations`).

**Cliente:** Quanto custa o Takamine GD20?

<details><summary>Tool calls</summary>

```
get_product({"name_or_id": "Takamine GD20"})
  → {"encontrado": true, "produtos": [{"id": 95, "nome": "Takamine GD20 Dreadnought Natural", "categoria": "Violões", "disponibilidade": "disponível", "estoque": 5, "preco_tabela": "R$ 2.199,00", "preco_final": "R$ 2.199,00", "parcelamento": "até 12x sem juros de R$ 183,25", "promocao_ativa": null, "pix": "R$ 2.089,05 à vista no PIX (5% off)", "descricao": "Violão dreadnought Takamine com tampo sólido
```

</details>

**Empório:** O **Takamine GD20 Dreadnought Natural** está disponível em estoque (5 unidades) por **R$ 2.199,00**, sem promoção ativa no momento.

- **À vista no PIX:** R$ 2.089,05 (5% de desconto)
- **Parcelado:** até 12x sem juros de R$ 183,25

É um violão dreadnought com tampo sólido de cedro, costas e laterais em sapele, braço em mogno, cordas de aço e escala de 650 mm. Ele é indicado para fingerstyle, com timbre quente e definido.

Quer que eu veja alguma alternativa parecida?

---

**Cliente:** Mas ele não tava com 12% de desconto? E na Black Friday, vai ter desconto?

<details><summary>Tool calls</summary>

```
get_policy({"section": "promocoes_e_descontos"})
  → {"secao": "promocoes_e_descontos", "texto": "# 6. Promoções e Descontos\n\n## 6.1 Tipos de Promoção\n\nA Empório da Música realiza promoções periódicas ao longo do ano. As principais campanhas incluem:\n\n- Aniversário da Loja (Agosto): descontos de 10% a 25% em itens selecionados.\n- Black Friday (Novembro): descontos de 15% a 30% em todo o catálogo.\n- Volta às Aulas (Fevereiro): descontos espec
```

</details>

**Empório:** Sim, o Takamine GD20 teve a **Oferta Especial de 12%**, mas essa promoção já **encerrou**. Por isso, hoje ele está pelo preço normal de **R$ 2.199,00**.

Sobre a Black Friday: a loja costuma fazer campanhas em novembro, mas não há nenhuma promoção ativa para o violão agora. Não posso confirmar desconto para novembro deste ano, então o melhor é acompanhar os nossos canais. Se quiser, posso verificar outros violões em promoção no catálogo.

---

**Cliente:** Entendi. E o Giannini GF-3D, vocês têm?

<details><summary>Tool calls</summary>

```
get_product({"name_or_id": "Giannini GF-3D"})
  → {"encontrado": true, "produtos": [{"id": 96, "nome": "Giannini GF-3D Dreadnought Sunburst", "categoria": "Violões", "disponibilidade": "esgotado no momento", "estoque": 0, "preco_tabela": "R$ 799,90", "preco_final": "R$ 799,90", "parcelamento": "até 7x sem juros de R$ 114,27", "promocao_ativa": null, "pix": "R$ 759,90 à vista no PIX (5% off)", "descricao": "Violão dreadnought com corpo amplo e aca
search_products({"category": "Violões", "query": "dreadnought aço"})
  → {"total_encontrado": 22, "produtos": [{"id": 107, "nome": "Shelby SGD-195E Elétrico Aço Sunburst", "categoria": "Violões", "disponibilidade": "disponível", "estoque": 6, "preco_tabela": "R$ 799,00", "preco_final": "R$ 799,00", "parcelamento": "até 7x sem juros de R$ 114,14", "promocao_ativa": null, "pix": "R$ 759,05 à vista no PIX (5% off)"}, {"id": 89, "nome": "Shelby SN-100 Folk Aço Preto", "cat
```

</details>

**Empório:** O **Giannini GF-3D Dreadnought Sunburst** está **esgotado** no momento. As promoções antigas dele (Semana do Músico, 18% e 40%) já encerraram, então o preço atual seria R$ 799,90 quando voltar.

Alguns violões de aço disponíveis em estoque:

- **Tagima Woodstock Dreadnought Natural:** R$ 899,00 (PIX R$ 854,05)
- **Yamaha FG800 Dreadnought Natural:** R$ 1.299,00 (PIX R$ 1.234,05)
- **Giannini GF-1R Aço Folk Sunburst:** R$ 579,90 (PIX R$ 550,90)
- **Yamaha F310 Aço Natural:** R$ 699,90 (PIX R$ 664,90)
- **Shelby SGD-195E Elétrico Aço Sunburst:** R$ 799,00 (PIX R$ 759,05)

Quer que eu detalhe algum deles?

---
