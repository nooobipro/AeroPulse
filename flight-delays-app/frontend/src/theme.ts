import { createTheme, MantineColorsTuple } from '@mantine/core';

// Палитра взята из аэропортовой навигации: тёмно-синее табло, янтарный для «задержан», зелёный для «вовремя».
export const COLORS = {
  ink: '#0E2238',
  board: '#10243E',
  boardLine: '#2A4466',
  paper: '#F3F5F7',
  line: '#D5DBE2',
  amber: '#F5B301',
  amberDeep: '#C98A00',
  green: '#1F8A70',
  red: '#C73E3A',
  muted: '#5B6B7D',
};

const navy: MantineColorsTuple = [
  '#EAF0F7', '#D2DEEC', '#A5BCD8', '#7798C3', '#507BB1', '#366AA8', '#2A5F9F', '#1F4E86', '#17406F', '#10243E',
];
const amber: MantineColorsTuple = [
  '#FFF8E1', '#FFEFBB', '#FFE38A', '#FFD45A', '#FFC736', '#F5B301', '#DB9F00', '#B98300', '#926800', '#6F4F00',
];

export const theme = createTheme({
  primaryColor: 'navy',
  primaryShade: 9,
  colors: { navy, amber },
  fontFamily: '"Fira Sans", system-ui, -apple-system, "Segoe UI", sans-serif',
  headings: { fontFamily: '"Fira Sans Condensed", "Fira Sans", system-ui, sans-serif', fontWeight: '700' },
  defaultRadius: 'sm',
  black: COLORS.ink,
  components: {
    Paper: { defaultProps: { withBorder: true, radius: 'sm' } },
    Button: { defaultProps: { radius: 'sm' } },
    Table: { defaultProps: { verticalSpacing: 6, horizontalSpacing: 'sm' } },
  },
});
