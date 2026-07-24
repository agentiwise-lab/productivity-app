/**
 * The tab bar, hand-built.
 *
 * `@react-navigation`'s own bar cannot draw the selected indicator this design
 * uses, a 24x2 bar hanging off the top edge of the item, so the whole thing is
 * passed through the `tabBar` prop instead. That also puts the blur under our
 * control: the bar is the canvas at 74% behind a real blur, so a bright row
 * scrolling underneath tints it rather than disappearing behind a flat block.
 *
 * There is no count badge. A number on the Feed tab is a second opinion about
 * urgency competing with the ring on Your day, and two of those disagree the
 * moment one of them is stale.
 */

import React from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { BlurView } from 'expo-blur';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { inset, size, useTheme, haptics } from '../theme';
import { Icon, type GlyphName } from './Icon';
import { T } from './ui';

const GLYPHS: Record<string, GlyphName> = {
  Day: 'sun',
  Feed: 'cards',
  Later: 'clock',
  Activity: 'pulse',
  You: 'user',
};

export function TabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const c = useTheme();

  return (
    <View
      style={[
        styles.bar,
        { backgroundColor: c.tabBar, borderTopColor: c.hairline },
      ]}
    >
      {/* Behind the translucent fill rather than over it: a blur on top would
          blur the labels as well as what is under them. */}
      {Platform.OS !== 'web' ? (
        <BlurView
          intensity={24}
          tint={c.mode === 'dark' ? 'dark' : 'light'}
          style={StyleSheet.absoluteFill}
        />
      ) : null}

      {state.routes.map((route, index) => {
        const on = state.index === index;
        const label = descriptors[route.key]?.options.title ?? route.name;
        return (
          <Pressable
            key={route.key}
            accessibilityRole="tab"
            accessibilityState={on ? { selected: true } : {}}
            onPress={() => {
              if (on) return;
              haptics.select();
              navigation.navigate(route.name);
            }}
            style={styles.item}
          >
            {on ? (
              <View style={[styles.indicator, { backgroundColor: c.high }]} />
            ) : null}
            {/* Filled when selected, outlined when not. That is how a platform
                bar signals selection, and unlike a tint it still reads for
                someone who cannot separate the two colours. */}
            <Icon
              name={GLYPHS[route.name] ?? 'cards'}
              size={25}
              color={on ? c.high : c.low}
              weight={on ? 'fill' : 'regular'}
            />
            <T role="label" tone={on ? 'high' : 'low'} style={styles.label}>
              {label}
            </T>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    height: size.tabBar,
    paddingBottom: inset.bottom,
    flexDirection: 'row',
    borderTopWidth: 0.5,
    overflow: 'hidden',
  },
  item: {
    flex: 1,
    height: size.tabItem,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
  },
  indicator: {
    position: 'absolute',
    top: 0,
    width: 24,
    height: 2,
    borderBottomLeftRadius: 2,
    borderBottomRightRadius: 2,
  },
  // 12 rather than the role's 16, so icon plus label fits 49 with the gap.
  label: { lineHeight: 12 },
});
