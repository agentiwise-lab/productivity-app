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
                padding: space.sm,
                overflow: 'hidden',
                borderWidth: 1,
                borderColor: 'transparent',
              },
              on ? { backgroundColor: c.surface, borderColor: c.border } : null,
            ]}
          >
            <View
              style={{
                position: 'absolute',
                left: 0,
                // Inset by the cell's own padding when resting; full height
                // when selected, which is the shape a bar makes when the row
                // it marks becomes the row you are reading.
                top: on ? 0 : space.sm,
                bottom: on ? 0 : space.sm,
                width: 3,
                borderRadius: radius.pill,
                backgroundColor: c.hue[category as Category],
              }}
            />
            <View
              style={{
                marginLeft: space.sm,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <Icon
                name={CATEGORY_GLYPH[category]}
                size={20}
                color={c.hue[category as Category]}
              />
              <T role="title" numeric tone={on ? 'high' : 'mid'}>
                {String(counts[category])}
              </T>
            </View>
            <T
              role="label"
              tone={on ? 'high' : 'low'}
              style={{ marginLeft: space.sm, marginTop: space.xxs }}
            >
              {CATEGORY_LABEL[category as Category]}
            </T>
          </Pressable>
        );
      })}
    </View>
  );
}
