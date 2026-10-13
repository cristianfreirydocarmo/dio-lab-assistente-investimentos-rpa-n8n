// Código do nó "Cruzar Perfil x Investimentos" (Code node, modo "Run Once for All Items").
// Mantido aqui só para leitura/versionamento: o mesmo código está embutido no n8n/workflow.json.
//
// Entrada:
//   - $input.all()  -> linhas do data.csv (perfil, produto, minimo, rentabilidade)
//   - Webhook body  -> { clientes: [{ nome, email, saldo, perfil }], usar_ia?: boolean }
// Saída: um item por cliente, já com o produto recomendado e as alternativas.

// Estimativa usada só para comparar "IPCA+6.0%" com taxas prefixadas.
const IPCA_ESTIMADO = 4.5;

const webhook = $('Webhook - Receber Clientes').first().json;
const body = webhook.body || {};
const clientes = Array.isArray(body) ? body : (body.clientes || []);
const usarIa = body.usar_ia === true || String(webhook.query?.ia).toLowerCase() === 'true';

// "R$ 12.500,00" -> 12500
const paraNumero = (valor) =>
  Number(String(valor).replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.')) || 0;

const formatarReais = (valor) =>
  valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// "13.0%" -> 13 | "IPCA+6.0%" -> 10.5 | "Variável" -> null
const taxaAnual = (rentabilidade) => {
  const texto = String(rentabilidade).trim();
  const ipca = texto.match(/^IPCA\s*\+\s*([\d.,]+)%$/i);
  if (ipca) return IPCA_ESTIMADO + Number(ipca[1].replace(',', '.'));
  const fixa = texto.match(/^([\d.,]+)%$/);
  return fixa ? Number(fixa[1].replace(',', '.')) : null;
};

const normalizar = (texto) => String(texto).trim().toLowerCase();

const produtos = $input.all().map(({ json }) => ({
  perfil: String(json.perfil).trim(),
  produto: String(json.produto).trim(),
  minimo: paraNumero(json.minimo),
  rentabilidade: String(json.rentabilidade).trim(),
  taxa: taxaAnual(json.rentabilidade),
}));

const descrever = (p) =>
  `${p.produto} (rentabilidade ${p.rentabilidade}, aporte mínimo ${formatarReais(p.minimo)})`;

return clientes.map((cliente) => {
  const saldo = paraNumero(cliente.saldo);
  const doPerfil = produtos.filter((p) => normalizar(p.perfil) === normalizar(cliente.perfil));
  const elegiveis = doPerfil.filter((p) => p.minimo <= saldo);

  // Regra: maior rentabilidade conhecida; se nenhuma for numérica (renda variável),
  // o produto de maior aporte mínimo que o saldo comporta.
  const ordenados = [...elegiveis].sort(
    (a, b) => (b.taxa ?? -1) - (a.taxa ?? -1) || b.minimo - a.minimo,
  );
  const recomendado = ordenados[0] || null;
  const alternativas = ordenados.slice(1);

  // Saldo abaixo de todos os mínimos: indica o produto de entrada mais acessível.
  const maisAcessivel = [...doPerfil].sort((a, b) => a.minimo - b.minimo)[0] || null;

  let recomendacaoTexto;
  if (recomendado) {
    recomendacaoTexto = descrever(recomendado);
  } else if (maisAcessivel) {
    recomendacaoTexto = `juntar ${formatarReais(maisAcessivel.minimo - saldo)} para começar com ${descrever(maisAcessivel)}`;
  } else {
    recomendacaoTexto = 'falar com um especialista, pois não temos produtos cadastrados para esse perfil';
  }

  return {
    json: {
      nome: cliente.nome,
      primeiro_nome: String(cliente.nome).trim().split(/\s+/)[0],
      email: cliente.email,
      perfil: cliente.perfil,
      saldo: cliente.saldo,
      saldo_numero: saldo,
      produto_recomendado: recomendado ? recomendado.produto : null,
      recomendacao_texto: recomendacaoTexto,
      alternativas: alternativas.map((p) => p.produto),
      alternativas_texto: alternativas.length ? alternativas.map(descrever).join('; ') : 'nenhuma no momento',
      produtos_do_perfil: doPerfil.map(descrever).join('; '),
      usar_ia: usarIa,
    },
  };
});
