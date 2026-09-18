const PALETTE =
  "slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose";
const HEX = /#[0-9A-Fa-f]{3,8}\b/;
const RAW_PALETTE = new RegExp(
  String.raw`\b(?:bg|text|border|from|to|via|ring|outline|fill|stroke|divide|placeholder|accent|caret)-(?:${PALETTE})-\d{2,3}\b`,
);

function check(context, node, value) {
  if (typeof value !== "string") {
    return;
  }
  if (HEX.test(value)) {
    context.report({
      node,
      message:
        "Use semantic design tokens from styles.css, not hex colours in components.",
    });
  }
  if (RAW_PALETTE.test(value)) {
    context.report({
      node,
      message:
        "Use semantic design tokens, not raw Tailwind palette classes in components.",
    });
  }
}

/** @type {import("eslint").Rule.RuleModule} */
const noRawDesignTokens = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Disallow hex colours and raw Tailwind palette utilities in components.",
    },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        check(context, node, node.value);
      },
      TemplateElement(node) {
        check(context, node, node.value.raw);
      },
    };
  },
};

/** @type {import("eslint").ESLint.Plugin} */
const plugin = {
  meta: { name: "career-assistant-design", version: "0.1.0" },
  rules: {
    "no-raw-design-tokens": noRawDesignTokens,
  },
};

export default plugin;
