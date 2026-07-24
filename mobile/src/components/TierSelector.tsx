/**
 * Three cells that actually select.
 *
 * The counts were symmetric, which was right, but nothing happened when you
 * touched them and nothing showed which was active. Now tapping one swaps the
 * list beneath from the day's meetings to that category's items, and tapping it
 * again clears it. No scroller, no second screen.
 *
 * Selection is signalled four ways at once: a fill, a border, the bar growing
 * to full height, and the label lifting up the contrast ladder. Any one of them
 * would do on a good screen in good light. Four of them means the state
 * survives greyscale, sunlight, and a glance.
 */

import React from 'react';
import { Pressable, View } from 'react-native';
import { CATEGORY_GLYPH, Icon } from './Icon';
import { T } from './ui';
import {
  CATEGORY_LABEL,
  haptics,
  radius,
  space,
  useTheme,
  type Category,
} from '../theme';

export type SelectableTier = 'urgent' | 'byEod' | 'canWait';

const CELLS: SelectableTier[] = ['urgent', 'byEod', 'canWait'];

export function TierSelector({
  counts,
  selected,
  onSelect,
}: {
  counts: Record<SelectableTier, number>;
  selected: SelectableTier | null;
  onSelect: (next: SelectableTier | null) => void;
}) {
  const c = useTheme();
  return (
    <View
      style={{
        flexDirection: 'row',
        gap: space.xs,
        paddingHorizontal: space.md,
        marginTop: space.lg,
      }}
    >
      {CELLS.map((category) => {
        const on = category === selected;
        return (
          <Pressable
            key={category}
            accessibilityRole="tab"
            accessibilityState={on ? { selected: true } : {}}
            onPress={() => {
              haptics.select();
              onSelect(on ? null : category);
            }}
            style={[
              {
                flex: 1,
                borderRadius: radius.md,
                // A step tighter than the rest of the app's cards, and
                // deliberately. Three cells of a 22pt number over an 11pt
                // label need 8 to sit as one band under the ring; at 12 they
                // read as three separate tiles competing with it.
                paddingVertical: space.xs,
                paddingHorizontal: space.xs,
                overflow: 'hidden',
                borderWidth: 1,
                borderColor: 'transparent',
              },
              // A resting cell is still a card. Without a fill the coloured
              // rule had nothing to sit against, so the row read as three
              // saturated strokes floating on the canvas rather than as three
              // controls; selection then had to be carried by the fill
              // appearing, which is a bigger jump than a state change deserves.
              { backgroundColor: c.surface },
              on ? { backgroundColor: c.raised, borderColor: c.border } : null,
            ]}
          >
            <View
              style={{
                position: 'absolute',
                left: 0,
                // Inset by the cell's own padding when resting; full height
                // when selected, which is the shape a bar makes when the row
                // it marks becomes the row you are reading.
                top: on ? 0 : space.xs,
                bottom: on ? 0 : space.xs,
                width: 2,
                borderRadius: radius.pill,
                backgroundColor: c.hue[category as Category],
              }}
            />
            <View
              style={{
                marginLeft: space.xs,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <Icon
                name={CATEGORY_GLYPH[category]}
                size={17}
                color={c.hue[category as Category]}
              />
              <T role="title" numeric tone={on ? 'high' : 'mid'}>
                {String(counts[category])}
              </T>
            </View>
            <T
              role="label"
              tone={on ? 'high' : 'low'}
              style={{ marginLeft: space.xs, marginTop: space.xxs }}
            >
              {CATEGORY_LABEL[category as Category]}
            </T>
          </Pressable>
        );
      })}
    </View>
  );
}
