import type { TalentBranch, TalentCatalog, TalentNode } from "@/services/talent-service";

/**
 * Regras de exibição dos talentos. O servidor é a autoridade: estas funções
 * só decidem o que mostrar (disponível, bloqueado, motivo), nunca concedem nada.
 */

export type NodeStatus = "owned" | "available" | "locked" | "exclusive" | "unavailable";

export interface NodeEvaluation {
  status: NodeStatus;
  /** Requisitos que ainda faltam, em português. */
  missing: string[];
}

export interface EvaluationContext {
  catalog: TalentCatalog;
  nodesById: Map<string, TalentNode>;
  branchesById: Map<string, TalentBranch>;
  owned: ReadonlySet<string>;
  level: number;
  pointsAvailable: number;
}

export const STAT_LABELS: Record<string, string> = {
  crop_yield: "Produção das colheitas",
  crop_grow_time: "Tempo de crescimento",
  extra_harvest_chance: "Chance de colheita extra",
  seed_save_chance: "Chance de poupar a semente",
  xp_gain: "XP ganho",
  sell_price: "Preço de venda",
  market_fee: "Taxa de venda",
  production_time: "Tempo de fabricação",
  production_yield: "Rendimento da fabricação",
  production_saving: "Chance de lote sem gastar insumos",
  animal_yield: "Produtos dos animais",
  animal_speed: "Tempo de produção dos animais",
  feed_efficiency: "Rendimento da ração",
};

/** Nomes dos escopos: culturas, espécies, produtos e estações. */
const CROP_NAMES: Record<string, string> = {
  milho: "Milho",
  cenoura: "Cenoura",
  tomate: "Tomate",
  morango: "Morango",
  cafe: "Café",
  galinha: "Galinhas",
  vaca: "Vacas",
  ovelha: "Ovelhas",
  ovo: "Ovos",
  leite: "Leite",
  la: "Lã",
  farinha: "Farinha",
  pao: "Pão",
  bolo: "Bolo",
  queijo: "Queijo",
  manteiga: "Manteiga",
  moinho: "Moinho",
  padaria: "Padaria",
  queijaria: "Queijaria",
};

export function buildContext(
  catalog: TalentCatalog,
  owned: ReadonlySet<string>,
  level: number,
  pointsAvailable: number,
): EvaluationContext {
  return {
    catalog,
    nodesById: new Map(catalog.nodes.map((node) => [node.id, node])),
    branchesById: new Map(catalog.branches.map((branch) => [branch.id, branch])),
    owned,
    level,
    pointsAvailable,
  };
}

export function spentInBranch(ctx: EvaluationContext, branchId: string): number {
  let total = 0;
  for (const id of ctx.owned) {
    const node = ctx.nodesById.get(id);
    if (node && node.branch === branchId) {
      total += node.cost;
    }
  }
  return total;
}

/** Maior investimento possível no ramo (talentos exclusivos contam uma vez). */
export function branchMaxPath(catalog: TalentCatalog, branchId: string): number {
  const seenGroups = new Set<string>();
  let total = 0;
  for (const node of catalog.nodes) {
    if (node.branch !== branchId) {
      continue;
    }
    if (node.exclusive_group) {
      if (seenGroups.has(node.exclusive_group)) {
        continue;
      }
      seenGroups.add(node.exclusive_group);
    }
    total += node.cost;
  }
  return total;
}

export function evaluateNode(node: TalentNode, ctx: EvaluationContext): NodeEvaluation {
  const branch = ctx.branchesById.get(node.branch);
  if (branch && !branch.available) {
    return { status: "unavailable", missing: ["Este ramo ainda não está disponível."] };
  }
  if (ctx.owned.has(node.id)) {
    return { status: "owned", missing: [] };
  }

  if (node.exclusive_group) {
    for (const id of ctx.owned) {
      if (ctx.nodesById.get(id)?.exclusive_group === node.exclusive_group) {
        return { status: "exclusive", missing: ["Você já escolheu outro talento mestre deste ramo."] };
      }
    }
  }

  const missing: string[] = [];
  if (ctx.level < node.min_level) {
    missing.push(`Nível ${node.min_level} (você está no ${ctx.level})`);
  }
  for (const id of node.requires) {
    if (!ctx.owned.has(id)) {
      missing.push(`Talento «${ctx.nodesById.get(id)?.name ?? id}»`);
    }
  }
  if (node.requires_any.length > 0 && !node.requires_any.some((id) => ctx.owned.has(id))) {
    const names = node.requires_any.map((id) => `«${ctx.nodesById.get(id)?.name ?? id}»`);
    missing.push(`Um destes talentos: ${names.join(" ou ")}`);
  }
  for (const [branchId, needed] of Object.entries(node.branch_points)) {
    const spent = spentInBranch(ctx, branchId);
    if (spent < needed) {
      const name = ctx.branchesById.get(branchId)?.name ?? branchId;
      missing.push(`${needed} pontos em ${name} (${spent}/${needed})`);
    }
  }
  if (node.cost > ctx.pointsAvailable) {
    missing.push(`${node.cost} ponto(s) de talento (disponíveis: ${ctx.pointsAvailable})`);
  }

  return { status: missing.length === 0 ? "available" : "locked", missing };
}

/** Texto legível de um efeito, ex.: «Milho: Produção das colheitas +6%». */
export function describeEffect(stat: string, valueBp: number, scope: string | null): string {
  const label = STAT_LABELS[stat] ?? stat;
  const sign = valueBp > 0 ? "+" : "−";
  const amount = Math.abs(valueBp) / 100;
  const formatted = amount.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const unit = stat === "market_fee" ? " pt" : "%";
  const where = scope ? `${CROP_NAMES[scope] ?? scope}: ` : "";
  return `${where}${label} ${sign}${formatted}${unit}`;
}
