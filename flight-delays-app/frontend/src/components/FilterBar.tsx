import { Button, Collapse, Group, Input, MultiSelect, Paper, RangeSlider, Select, SegmentedControl, SimpleGrid } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { IconAdjustmentsHorizontal, IconFilterOff } from '@tabler/icons-react';
import { useEffect, useMemo, useState } from 'react';
import { useFilterOptions } from '../api/hooks';
import { Filters, isDefault } from '../filters';
import { fmtHour, fmtPeriod } from '../utils/format';

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
}

const HOUR_MARKS = [0, 6, 12, 18, 23].map((v) => ({ value: v, label: String(v).padStart(2, '0') }));

/** Единый набор фильтров: применяется ко всем показателям и графикам панели. */
export function FilterBar({ filters, onChange, onReset }: Props) {
  const { data: opts } = useFilterOptions();
  const isMobile = useMediaQuery('(max-width: 48em)');
  const [open, setOpen] = useState(false);
  const expanded = !isMobile || open; // на телефоне фильтры свёрнуты, чтобы показатели были видны сразу
  const activeCount = [filters.airlines.length > 0, filters.airports.length > 0, !!filters.periodFrom || !!filters.periodTo,
    filters.hourFrom !== 0 || filters.hourTo !== 23, filters.threshold !== 0, filters.avgMode !== 'all'].filter(Boolean).length;
  const [hours, setHours] = useState<[number, number]>([filters.hourFrom, filters.hourTo]);
  useEffect(() => setHours([filters.hourFrom, filters.hourTo]), [filters.hourFrom, filters.hourTo]);

  const airlines = useMemo(() => (opts?.airlines ?? []).map((a) => ({ value: String(a.id), label: a.name })), [opts]);
  const airports = useMemo(
    () => (opts?.airports ?? []).map((a) => ({ value: String(a.id), label: `${a.code} — ${a.city || a.name || a.code}` })),
    [opts],
  );
  const periods = useMemo(() => (opts?.periods ?? []).map((p) => ({ value: p, label: fmtPeriod(p) })), [opts]);

  return (
    <Paper p="md" className="sticky-filters" shadow="xs">
      {isMobile && (
        <Button
          variant="subtle" fullWidth justify="space-between" leftSection={<IconAdjustmentsHorizontal size={18} />}
          onClick={() => setOpen((o) => !o)} aria-expanded={open} mb={open ? 'sm' : 0}
        >
          Фильтры{activeCount ? ` (${activeCount})` : ''}
        </Button>
      )}
      <Collapse in={expanded}>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="sm" verticalSpacing="sm">
        <MultiSelect
          label="Авиакомпании" placeholder={filters.airlines.length ? undefined : 'Все'} data={airlines} searchable clearable
          value={filters.airlines.map(String)} onChange={(v) => onChange({ airlines: v.map(Number) })}
          nothingFoundMessage="Не найдено" maxDropdownHeight={260}
        />
        <MultiSelect
          label="Аэропорты вылета" placeholder={filters.airports.length ? undefined : 'Все'} data={airports} searchable clearable limit={60}
          value={filters.airports.map(String)} onChange={(v) => onChange({ airports: v.map(Number) })}
          nothingFoundMessage="Не найдено" maxDropdownHeight={260}
        />
        <Group grow gap="xs" align="flex-start">
          <Select
            label="Период с" placeholder="Начало" data={periods} clearable searchable value={filters.periodFrom}
            onChange={(v) => onChange({ periodFrom: v, ...(v && filters.periodTo && v > filters.periodTo ? { periodTo: v } : {}) })}
          />
          <Select
            label="по" placeholder="Конец" data={periods} clearable searchable value={filters.periodTo}
            onChange={(v) => onChange({ periodTo: v, ...(v && filters.periodFrom && v < filters.periodFrom ? { periodFrom: v } : {}) })}
          />
        </Group>
        <Input.Wrapper label={`Время вылета: ${fmtHour(hours[0])} — ${fmtHour(hours[1])}`}>
          <RangeSlider
            mt={10} mb={22} min={0} max={23} step={1} minRange={0} value={hours} marks={HOUR_MARKS}
            label={(v) => fmtHour(v)} color="amber.5" onChange={setHours}
            onChangeEnd={([a, b]) => onChange({ hourFrom: a, hourTo: b })}
          />
        </Input.Wrapper>
      </SimpleGrid>

      <Group mt="sm" gap="lg" align="flex-end" wrap="wrap">
        <Input.Wrapper label="Считать задержанным рейс с опозданием">
          <SegmentedControl
            size="xs" value={String(filters.threshold)} onChange={(v) => onChange({ threshold: v === '15' ? 15 : 0 })}
            data={[{ value: '0', label: 'более 0 минут' }, { value: '15', label: '15 минут и более' }]}
          />
        </Input.Wrapper>
        <Input.Wrapper label="Средняя задержка">
          <SegmentedControl
            size="xs" value={filters.avgMode} onChange={(v) => onChange({ avgMode: v === 'delayed' ? 'delayed' : 'all' })}
            data={[{ value: 'all', label: 'по всем рейсам' }, { value: 'delayed', label: 'только по задержанным' }]}
          />
        </Input.Wrapper>
        <Button variant="default" size="xs" leftSection={<IconFilterOff size={16} />} onClick={onReset} disabled={isDefault(filters)}>
          Сбросить фильтры
        </Button>
      </Group>
      </Collapse>
    </Paper>
  );
}
