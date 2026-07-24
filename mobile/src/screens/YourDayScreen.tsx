/**
 * Your day: the ring, the selector, and one list.
 *
 * The list beneath the selector is the same space showing two different things.
 * With nothing selected it is the day's meetings, which is what the screen is
 * for when nothing is pressing. Select a category and it is that category's
 * items. Tapping the selected cell again clears it.
 *
 * The feed slider is gone. Swiping cards is what the Feed tab is, and having it
 * here as well meant two places to do the same thing, one of them cramped.
 */

import React, { useMemo, useState } from 'react';
import { RefreshControl, ScrollView, View } from 'react-native';
import Animated, {
  useAnimatedScrollHandler,
  useSharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { CATEGORY_OF_TIER, space, topInset, useTheme } from '../theme';
import { CollapsedTitle, ScreenHeader } from '../components/Chrome';
import { DayRing, type Meeting } from '../components/YourDayCard';
import {
  TierSelector,
  type SelectableTier,
} from '../components/TierSelector';
import { Row } from '../components/ListRow';
import { BrandMark } from '../components/BrandMark';
import { SectionLabel, T } from '../components/ui';
import { Clear, NoMeetingsLeft, NothingConnected, Skeleton, StaleBanner } from '../components/states';
import { ago, deadlineLabel } from '../lib/time';
import { subtext } from '../lib/subtext';
import type { FeedRow } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

interface Props {
  rows: FeedRow[];
  loading: boolean;
  stale: boolean;
  fetchedAt: Date | null;
  meetings: Meeting[];
  connectedCount: number;
  sourcesUnknown: boolean;
  sourcesLoading: boolean;
  onRefresh: () => Promise<void>;
  onOpen: (row: FeedRow) => void;
  onConnect: () => void;
}

export function YourDayScreen({
  rows,
  loading,
  stale,
  fetchedAt,
  meetings,
  connectedCount,
  sourcesUnknown,
  sourcesLoading,
  onRefresh,
  onOpen,
  onConnect,
}: Props) {
  const c = useTheme();
  const insets = useSafeAreaInsets();
  const [selected, setSelected] = useState<SelectableTier | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const scrollY = useSharedValue(0);
  const onScroll = useAnimatedScrollHandler((event) => {
    scrollY.value = event.contentOffset.y;
  });

  const live = useMemo(
    () => rows.filter((row) => row.status === 'unread' && row.tier !== 'noise'),
    [rows],
  );

  const counts = useMemo(
    () => ({
      urgent: live.filter((row) => row.tier === 'urgent').length,
      byEod: live.filter((row) => row.tier === 'today').length,
      canWait: live.filter((row) => row.tier === 'can_wait').length,
    }),
    [live],
  );

  /**
   * What is still to come. The section is headed "Next", and it was listing
   * every meeting of the day including the ones already over: at 22:00 it
   * offered a 13:15 stand-up as the next thing, directly above a line reading
   * "Nothing else in the calendar today". Both were drawn from this same array;
   * only one of them was filtering it.
   */
  const ahead = useMemo(() => {
    const now = new Date();
    return meetings
      .filter((meeting) => meeting.end > now)
      .sort((a, b) => a.start.getTime() - b.start.getTime());
  }, [meetings]);

  const heldBack = rows.length - live.length;
  const shown = selected
    ? live.filter((row) => CATEGORY_OF_TIER[row.tier] === selected)
    : [];

  const nothingConnected =
    !sourcesLoading && !sourcesUnknown && connectedCount === 0;

  return (
    <View style={{ flex: 1, backgroundColor: c.canvas }}>
      <AnimatedScrollView
        onScroll={onScroll}
        scrollEventThrottle={16}
        contentContainerStyle={{
          paddingTop: topInset(insets.top),
          paddingBottom: space.xl,
        }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            tintColor={c.mid}
            onRefresh={async () => {
              setRefreshing(true);
              await onRefresh();
              setRefreshing(false);
            }}
          />
        }
      >
        <ScreenHeader eyebrow={dateLine()} title={greeting()} />
        {stale ? <StaleBanner fetchedAt={fetchedAt} /> : null}

        {nothingConnected ? (
          <NothingConnected onConnect={onConnect} />
        ) : (
          <>
            <DayRing meetings={meetings} counts={counts} />
            <TierSelector
              counts={counts}
              selected={selected}
              onSelect={setSelected}
            />

            {selected ? (
              <>
                <SectionLabel
                  label={LABEL[selected]}
                  count={`${shown.length} ${shown.length === 1 ? 'item' : 'items'}`}
                />
                {shown.length === 0 ? (
                  <Clear heldBack={heldBack} filtered />
                ) : (
                  shown.map((row) => (
                    <Row
                      key={row.id}
                      category={CATEGORY_OF_TIER[row.tier]}
                      leading={<BrandMark source={row.source} size={32} />}
                      title={row.title}
                      subtitle={subtext(row)}
                      meta={deadlineLabel(row.deadline) ?? ago(row.occurred_at)}
                      submeta={row.repo || row.context_chip}
                      onPress={() => onOpen(row)}
                    />
                  ))
                )}
              </>
            ) : (
              <>
                {/* No heading over an empty section. "Next" above "You are
                    clear for today" is a label for a list that is not there. */}
                {ahead.length > 0 || loading ? <SectionLabel label="Next" /> : null}
                {loading && meetings.length === 0 ? (
                  <Skeleton rows={2} />
                ) : ahead.length === 0 ? (
                  <NoMeetingsLeft counts={counts} />
                ) : (
                  <>
                    {ahead.map((meeting, index) => (
                      <Row
                        key={`${meeting.title}-${index}`}
                        // A meeting has no category, so it takes the hue that
                        // means exactly that, and never shares a screen with a
                        // category hue in the same list.
                        category="none"
                        leading={
                          <T
                            role="heading"
                            numeric
                            tone={index === 0 ? 'high' : 'mid'}
                            style={{ width: 52 }}
                          >
                            {clock(meeting.start)}
                          </T>
                        }
                        title={meeting.title}
                        subtitle={durationLine(meeting)}
                        meta={duration(meeting)}
                      />
                    ))}
                    <View style={{ padding: space.md }}>
                      <T role="secondary" tone="mid">
                        {freeLine(ahead)}
                      </T>
                    </View>
                  </>
                )}
              </>
            )}
          </>
        )}
      </AnimatedScrollView>
      <CollapsedTitle title={greeting()} scrollY={scrollY} />
    </View>
  );
}

const LABEL: Record<SelectableTier, string> = {
  urgent: 'Urgent',
  byEod: 'By EOD',
  canWait: 'Can wait',
};

function greeting(now = new Date()): string {
  const hour = now.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function dateLine(now = new Date()): string {
  return now
    .toLocaleDateString(undefined, {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    })
    .replace(/,/g, '');
}

const clock = (date: Date) =>
  `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

function minutes(meeting: Meeting) {
  return Math.round((meeting.end.getTime() - meeting.start.getTime()) / 60000);
}

function duration(meeting: Meeting) {
  const total = minutes(meeting);
  return total >= 60 ? `${Math.floor(total / 60)}h${total % 60 || ''}` : `${total}m`;
}

function durationLine(meeting: Meeting) {
  return `${clock(meeting.start)} to ${clock(meeting.end)}`;
}

/**
 * Derived from the same meetings drawn above, so the picture and the number
 * cannot disagree.
 */
function freeLine(meetings: Meeting[], now = new Date()): string {
  const next = meetings
    .filter((meeting) => meeting.start > now)
    .sort((a, b) => a.start.getTime() - b.start.getTime())[0];
  if (!next) return 'Nothing else in the calendar today.';
  const gap = Math.round((next.start.getTime() - now.getTime()) / 60000);
  const label =
    gap >= 60 ? `${Math.floor(gap / 60)}h ${gap % 60}m` : `${Math.max(0, gap)}m`;
  return `${label} free before ${clock(next.start)}`;
}
