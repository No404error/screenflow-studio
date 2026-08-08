# ScreenFlow Web Studio — wireframes (Phase 0)

## Tokens

See `src/styles/tokens.css`: ink / paper / accent (teal), spacing scale, type ramp.

## 1. Welcome `/`

```
┌─────────────────────────────────────────────────────┐
│  ScreenFlow                                         │
│  Foreground vision automation                       │
│                                                     │
│  [ Open folder… ]   [ New project… ]                │
│                                                     │
│  Recent                                             │
│  · My Farm     E:\projects\farm                     │
│  · Blank       …                                    │
└─────────────────────────────────────────────────────┘
```

## 2. Page editor

```
┌ Nav ┐┌────────── Center ──────────────────┐┌ Run bar ┐
│ Vars││ Page: Lobby                        ││ Idle    │
│ Mac ││ [detect preview]                   │└─────────┘
│ Pag ││ Features grid …                    │
│  └─ ││ ▸ Decide / Post (collapsed)        │
└─────┘└────────────────────────────────────┘
```

## 3. State (tree | detail)

```
│ Tree          │ Detail: Case A                      │
│ ▸ Lobby       │ Score [template▾] [asset▾]          │
│   · Case A *  │ When  [var▾] [=] [value]            │
│   · ELSE      │ Actions (steps)                     │
│               │ Post …                              │
```

## 4. Variables

```
│ Name   │ Type │ Default │ Description │ Refs │
│ armed  │ bool │ false   │ …           │  3   │
```

## 5. Run drawer

```
════════ Idle · page — · state — · vars 0  [Start] ═══
│ Controls | Live Vars | Logs                         │
```
