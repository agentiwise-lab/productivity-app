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
import {
  Clear,
  NothingConnected,
  RingSkeleton,
  Skeleton,
  StaleBanner,
  TilesSkeleton,
} from '../components/states';
import { ago, deadlineLabel } from '../lib/time';
import { listSubtitle, primaryLine } from '../lib/rowText';
import type { FeedRow } from '../api/types';

const AnimatedScrollView = Animated.createAnimatedComponent(ScrollView);

interface Props {
  rows: FeedRow[];
  loading: boolean;
  /** The calendar's own loading, so the meetings section shows a skeleton until
   *  it has answered rather than flashing "no meetings" while it is still out. */
  dayLoading: boolean;
  stale: boolean;
  fetchedAt: Date | null;
  meetings: Meeting[];
  connectedCount: number;
  sourcesUnknown: boolean;
  sourcesLoading: boolean;
  onRefresh: () => Promise<void>;
  onOpen: (row: FeedRow) => void;
  onConnect: () => void;
  /** The display name, when set. Personalises the greeting; null falls back to
   *  the plain "Good evening". */
  name: string | null;
}

export function YourDayScreen({
  rows,
  loading,
  dayLoading,
  stale,
  fetchedAt,
  meetings,
  connectedCount,
  sourcesUnknown,
  sourcesLoading,
  onRefresh,
  onOpen,
  onConnect,
  name,
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
    const today = now.toDateString();
    // Today only: the calendar window can spill into tomorrow, and "next in N"
    // over a same-day count read as a bug when it pointed at tomorrow's meeting.
    return meetings
      .filter((meeting) => meeting.end > now && meeting.start.toDateString() === today)
      .sort((a, b) => a.start.getTime() - b.start.getTime());
  }, [meetings]);

  // Only today's meetings count toward the summary, in the device's own day: the
  // calendar window can spill an hour either side of midnight.
  const todayMeetings = useMemo(() => {
    const today = new Date().toDateString();
    return meetings.filter((m) => m.start.toDateString() === today);
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
        <ScreenHeader eyebrow={dateLine()} title={greeting(name)} />
        {stale ? <StaleBanner fetchedAt={fetchedAt} /> : null}

        {sourcesLoading ? (
          // Until we know what is connected, render nothing under the header
          // rather than the day ring. A new user has no connections, so the ring
          // would flash for a moment and then be replaced by the empty state.
          null
        ) : nothingConnected ? (
          <NothingConnected onConnect={onConnect} />
        ) : loading && counts.urgent + counts.byEod + counts.canWait === 0 ? (
          // Connected, but the feed is still hydrating: hold the ring's shape and
          // the day's rows with skeletons rather than flashing an empty ring.
          <>
            <RingSkeleton />
            <TilesSkeleton />
            <View style={{ marginTop: space.lg }}>
              <Skeleton rows={2} />
            </View>
          </>
        ) : (
          <>
            <DayRing meetings={todayMeetings} counts={counts} />
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
                      title={primaryLine(row)}
                      subtitle={listSubtitle(row)}
                      meta={deadlineLabel(row.deadline) ?? ago(row.occurred_at)}
                      onPress={() => onOpen(row)}
                    />
                  ))
                )}
              </>
            ) : dayLoading && meetings.length === 0 ? (
              // The calendar has not answered yet: a skeleton, never an early
              // "no meetings" that a moment later turns out to be wrong.
              <>
                <SectionLabel label="Today" />
                <Skeleton rows={2} />
              </>
            ) : (
              <>
                {/* Always a plain summary of the day, whether or not anything is
                    left on it: how many meetings today, and what is next. When
                    the calendar is clear but items remain, it points at the
                    categories above rather than leaving the screen blank. */}
                <View
                  style={{
                    paddingHorizontal: space.md,
                    marginTop: space.lg,
                    marginBottom: space.xs,
                  }}
                >
                  <T role="secondary" tone="low">
                    {daySummary(todayMeetings, ahead)}
                  </T>
                  {ahead.length === 0 ? (
                    // Read at the size a meeting row would have, so a clear day
                    // still has a line of real content where its list would be.
                    <T role="body" tone="high" style={{ marginTop: space.xs }}>
                      {workPrompt(counts)}
                    </T>
                  ) : null}
                </View>

                {ahead.length > 0 ? (
                  <>
                    <SectionLabel label="Next" tight />
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
                  </>
                ) : null}
              </>
            )}
          </>
        )}
      </AnimatedScrollView>
      <CollapsedTitle title={greeting(name)} scrollY={scrollY} />
    </View>
  );
}

const LABEL: Record<SelectableTier, string> = {
  urgent: 'Urgent',
  byEod: 'By EOD',
  canWait: 'Can wait',
};

function greeting(name: string | null, now = new Date()): string {
  const hour = now.getHours();
  const part =
    hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  return name ? `${part}, ${name}` : part;
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
 * One plain line about the day: how many meetings it holds and what comes next,
 * derived from the same array the ring and the list draw, so they cannot
 * disagree. Shown whether or not anything is still to come, which is what makes
 * an empty afternoon read as "done for the day" rather than as a broken screen.
 */
/**
 * The line under the day summary when the calendar is clear: it points at the
 * work still waiting in the categories above, so an empty afternoon is an
 * invitation to clear the queue rather than a blank half-screen.
 */
function workPrompt(counts: {
  urgent: number;
  byEod: number;
  canWait: number;
}): string {
  const total = counts.urgent + counts.byEod + counts.canWait;
  if (total === 0) return 'Nothing is waiting on you. Enjoy the quiet.';
  // The instruction alone, no count: the numbers are already on the cells the
  // sentence points at.
  return 'Pick a category above to work through what is left.';
}

function daySummary(today: Meeting[], ahead: Meeting[], now = new Date()): string {
  const count =
    today.length === 0
      ? 'No meetings today'
      : `${today.length} ${today.length === 1 ? 'meeting' : 'meetings'} today`;

  const next = ahead[0];
  if (!next) {
    return today.length === 0 ? count : `${count}, all done`;
  }

  const gap = Math.round((next.start.getTime() - now.getTime()) / 60000);
  if (gap <= 0) return `${count}, next now`;
  const wait =
    gap >= 60 ? `${Math.floor(gap / 60)}h ${gap % 60}m` : `${gap}m`;
  return `${count}, next in ${wait}`;
}
