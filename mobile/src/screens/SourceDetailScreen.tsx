/**
 * One source's board: what has been going on here.
 *
 * The summary numbers used to eat the screen. A 56pt hero, a row of glyphs and
 * a 2x2 tile grid spent about 470pt before a single listing row, on a screen
 * whose whole point is the listing. Compacted to roughly 290, and the
 * difference goes straight to the list.
 *
 * `headline[0]` is the hero. The rest become the summary grid. That is a
 * convention rather than a field, because a convention is cheaper and can be
 * reversed without a migration.
 *
 * **A breakdown row links only when it has a `url`.** That semantic is already
 * encoded by withholding the chevron, and it is worth keeping honest: a
 * Calendar frequency line is a summary with nowhere to go, and it renders
 * inert. The link glyph means something because of the rows that lack it.
 */

import React from 'react';
import { Linking, ScrollView, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { radius, space, useTheme } from '../theme';
import { BoardBar } from '../components/Chrome';
import { BrandMark } from '../components/BrandMark';
import { Row } from '../components/ListRow';
import { CircularAction, SectionLabel, T, Wash } from '../components/ui';
import { TopTint } from '../components/Bloom';
import { Explain, Skeleton } from '../components/states';
import type { Source, SourceDashboard, StatLine } from '../api/types';

/**
 * What a board is doing while it loads, in the source's own terms. A dashboard
 * is counted live at the provider, so it is genuinely slow: Slack asks about
 * every channel it can see. Four grey rectangles said none of that, so a board
 * that was working looked like a board that was broken.
 */
const LOADING_NOTE: Partial<Record<Source, string>> = {
  slack: 'Counting messages across every channel and DM. This one takes a moment.',
  github: 'Reading commits and pull requests across your repositories.',
  linear: 'Reading your issues and their states.',
  gmail: 'Grouping the last 30 days by sender.',
  calendar: 'Reading the last 30 days of meetings.',
};

export function SourceDetailScreen({
  dashboard,
  loading,
  onBack,
  onRefresh,
}: {
  dashboard: SourceDashboard | null;
  loading: boolean;
  onBack: () => void;
  onRefresh: () => void;
}) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const [hero, ...rest] = dashboard?.headline ?? [];

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas, paddingTop: insets.top }}>
      <BoardBar title={dashboard?.label ?? 'Source'} right="30 days" onBack={onBack}>
        {dashboard ? <BrandMark source={dashboard.source} size={24} /> : null}
      </BoardBar>

      {loading || !dashboard ? (
        <ScrollView contentContainerStyle={{ paddingTop: space.lg }}>
          <View style={{ paddingHorizontal: space.md, paddingBottom: space.md }}>
            <T role="secondary" tone="mid">
              {(dashboard?.source && LOADING_NOTE[dashboard.source]) ??
                'Counting the last 30 days.'}
            </T>
          </View>
          <Skeleton rows={5} />
        </ScrollView>
      ) : (
        <ScrollView contentContainerStyle={{ paddingBottom: space.xl }}>
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              gap: space.sm,
              paddingHorizontal: space.md,
              paddingVertical: space.lg,
              overflow: 'hidden',
            }}
          >
            <TopTint category="summary" width={393} height={140} />
            <View style={{ flex: 1 }}>
              <T role="display" numeric>
                {hero ? (hero.value_label ?? String(hero.value)) : '0'}
              </T>
              <T role="label" tone="low" style={{ marginTop: space.xxs }}>
                {hero?.label ?? 'Nothing recorded'}
              </T>
            </View>
            <CircularAction glyph="refresh" label="Refresh" onPress={onRefresh} />
          </View>

          {rest.length > 0 ? (
            <View
              style={{
                flexDirection: 'row',
                flexWrap: 'wrap',
                gap: space.xs,
                paddingHorizontal: space.md,
              }}
            >
              {rest.map((stat) => (
                <SummaryCard key={stat.label} stat={stat} />
              ))}
            </View>
          ) : null}

          {dashboard.breakdown.length > 0 ? (
            <>
              <SectionLabel label={dashboard.breakdown_title} tight />
              {dashboard.breakdown.map((line, index) => (
                <Row
                  key={`${line.label}-${index}`}
                  category="none"
                  leading={<BrandMark source={dashboard.source} size={32} />}
                  title={line.label}
                  subtitle={line.detail}
                  value={line.value_label ?? String(line.value)}
                  // The glyph is the link, so a row with nowhere to go has no
                  // glyph and no press state.
                  glyph={line.url ? 'external' : null}
                  onPress={line.url ? () => void Linking.openURL(line.url!) : undefined}
                />
              ))}
            </>
          ) : (
            <Explain
              title="Nothing in the last 30 days"
              body="This source is connected and answered, and it has had no activity in the window."
              top={space.lg}
            />
          )}

          {dashboard.unavailable.length > 0 ? (
            // One honest sentence, never a tile with a dash in it: a dash reads
            // as zero, and zero is a claim we cannot make here.
            <View style={{ paddingHorizontal: space.md, paddingTop: space.md }}>
              <T role="secondary" tone="low">
                Could not load: {dashboard.unavailable.join(', ')}.
              </T>
            </View>
          ) : null}
        </ScrollView>
      )}
    </View>
  );
}

function SummaryCard({ stat }: { stat: StatLine }) {
  const c = useTheme();
  return (
    <View
      style={{
        // Two per row. Three was too narrow for labels like "Remaining", which
        // wrapped their last letter onto a second line.
        width: '48.6%',
        flexGrow: 1,
        backgroundColor: c.surface,
        borderRadius: radius.md,
        padding: space.sm,
        overflow: 'hidden',
      }}
    >
      <Wash category="summary" height={80} direction="diagonal" alpha={0.16} />
      <T role="label" tone="low">
        {stat.label}
      </T>
      <T role="title" numeric style={{ marginTop: space.xxs }}>
        {stat.value_label ?? String(stat.value)}
      </T>
      {stat.detail ? (
        <T role="secondary" tone="mid" lines={1}>
          {stat.detail}
        </T>
      ) : null}
    </View>
  );
}
