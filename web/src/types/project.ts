/** Project DTO aligned with ScreenFlow v3 + Web Studio extensions. */

export type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue }

export interface ActionStep {
  op: string
  target?: string | number | null
  reason?: string | null
  hold?: number | null
  params?: Record<string, JsonValue> | null
}

export interface DecideParams {
  threshold?: number | null
  near?: number | null
  margin?: number | null
  on_close?: 'priority' | 'abstain' | null
}

export interface ScoreSpec {
  kind: 'template' | 'constant' | 'invert'
  key?: string | null
  roi?: number[] | null
  constant?: number
}

export interface PostListen {
  mode: string
  frames?: number | null
  settle?: number
  end_on_unknown?: boolean
  tree: StateNode[]
  params?: DecideParams
}

export interface StateNode {
  id: string
  name: string
  priority?: number
  else?: boolean
  is_else?: boolean
  score?: ScoreSpec | null
  children?: StateNode[]
  actions?: ActionStep[]
  post?: PostListen | null
  layer_params?: DecideParams
  when_var?: string | null
}

/** Template library file (pixels only — no search ROI). */
export interface PageAsset {
  name: string
  relpath: string
}

/**
 * Match setup (Visual): search area + template.
 * Lives on the page; features select via visual_id.
 */
export interface MatchSetup {
  id: string
  label: string
  asset: string
  template?: string
  search_roi?: number[] | null
  content_roi?: number[] | null
  complete?: boolean
}

/** @deprecated Use MatchSetup */
export type FeatureVisual = MatchSetup
/** @deprecated Use MatchSetup */
export type FeatureLink = MatchSetup

export interface FeatureDef {
  id: string
  label: string
  notes?: string
  visual_id?: string | null
  linked?: boolean
  has_visual?: boolean
  /** Resolved selected setup (API convenience). */
  link?: MatchSetup | null
  visual?: MatchSetup | null
}

export interface PageDoc {
  id: string
  name: string
  /** Convenience: artwork of recognize_with (from API). */
  detect?: string
  detect_priority?: number
  pair_with?: string | null
  recognize_with?: string | null
  /** Full-window canvas for match-setup editing (not used at runtime). */
  source?: string | null
  features?: Record<string, FeatureDef>
  /** Page-level match setups. */
  visuals?: Record<string, MatchSetup>
  /** Convenience ROI of recognize_with. */
  detect_roi?: number[] | null
  state_tree: StateNode[]
  decide_params?: DecideParams
  default_post?: PostListen | null
  assets?: PageAsset[]
}

export interface MacroDef {
  id: string
  name: string
  scope?: string
  steps: ActionStep[]
}

export interface RuntimeConfig {
  match_threshold: number
  poll_interval: number
  action_delay: number
  action_cooldown: number
  state_conf_margin: number
  state_near: number
  page_pair_margin: number
  page_detect_near: number
  ref_width: number
  ref_height: number
  verbose_log: boolean
  allow_redecide_during_action: boolean
  log_language: string
  hotkeys: Record<string, string>
}

export type VarType = 'bool' | 'number' | 'string'

export interface VarSchemaEntry {
  type?: VarType | string
  description?: string
}

export interface ProjectDTO {
  name: string
  version?: number
  root?: string
  runtime: RuntimeConfig
  macros: MacroDef[]
  pages: string[]
  page_pairs: string[][]
  page_docs: Record<string, PageDoc>
  vars?: Record<string, JsonValue>
  var_schema?: Record<string, VarSchemaEntry>
}

export type NavKind =
  | 'welcome'
  | 'variables'
  | 'macros'
  | 'macro'
  | 'pages'
  | 'pairs'
  | 'page'
  | 'state'

export interface NavSelection {
  kind: NavKind
  pageId?: string
  nodeId?: string
  macroId?: string
}

export interface Issue {
  level: 'error' | 'warning' | string
  text: string
}

export interface EngineStatus {
  mode?: string
  page_id?: string | null
  page_label?: string | null
  state?: string | null
  sticky?: boolean
  post_mode?: string | null
  post_reason?: string | null
  vars?: Record<string, JsonValue>
  error?: string
}
