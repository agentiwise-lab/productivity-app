/**
 * Screen chrome. There is no title bar on any screen.
 *
 * A dissolving title and a persistent bar were doing the same job twice, so the
 * bar is gone: the large line is content, sitting in the scroll view with the
 * rest of it, and it collapses into a 44pt blurred strip only once it has
 * actually left the screen. Nothing is reserved for a header that is not there.
 *
 * A source board is the one exception, and only because it needs somewhere to
 * put a back affordance.
 */

import React from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  interpolate,
  useAnimatedStyle,
  type SharedValue,
} from 'react-native-reanimated';
import { BlurView } from 'expo-blur';
import { inset, size, space, useTheme } from '../theme';
import { Icon } from './Icon';
import { T } from './ui';

/** The large line. Lives in the scroll view, because it is content. */
export function ScreenHeader({
  eyebrow,
  title,
}: {
  eyebrow: string;
  title: string;
}) {
  return (
    <View style={styles.header}>
      <T role="label" tone="low">
        {eyebrow}
      </T>
      <T role="display" style={{ marginTop: space.xxs }} lines={2}>
        {title}
      </T>
    </View>
  );
}

/**
 * What replaces it once it has scrolled away. Absolute, above the list, and
 * invisible until the large line has passed under it, so the two are never on
 * screen together saying the same thing.
 */
export function CollapsedTitle({
  title,
  scrollY,
  threshold = 64,
}: {
  title: string;
  scrollY: SharedValue<number>;
  threshold?: number;
}) {
  const c = useTheme();
  const style = useAnimatedStyle(() => ({
    opacity: interpolate(
      scrollY.value,
      [threshold - 16, threshold + 16],
      [0, 1],
      'clamp',
    ),
  }));

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        styles.collapsed,
        { top: inset.top, backgroundColor: c.tabBar, borderBottomColor: c.hairline },
        style,
      ]}
    >
      {Platform.OS !== 'web' ? (
        <BlurView
          intensity={24}
          tint={c.mode === 'dark' ? 'dark' : 'light'}
          style={StyleSheet.absoluteFill}
        />
      ) : null}
      <T role="heading" lines={1}>
        {title}
      </T>
    </Animated.View>
  );
}

/**
 * The board's bar. Keeps a back affordance, which is the whole reason it
 * survived the cull.
 */
export function BoardBar({
  title,
  right,
  onBack,
  children,
}: {
  title: string;
  right?: string;
  onBack: () => void;
  /** The source's mark, which sits between the chevron and the title. */
  children?: React.ReactNode;
}) {
  const c = useTheme();
  return (
    <View
      style={[
        styles.board,
        { backgroundColor: c.tabBar, borderBottomColor: c.hairline },
      ]}
    >
      {Platform.OS !== 'web' ? (
        <BlurView
          intensity={24}
          tint={c.mode === 'dark' ? 'dark' : 'light'}
          style={StyleSheet.absoluteFill}
        />
      ) : null}
      <Pressable onPress={onBack} hitSlop={12} accessibilityLabel="Back">
        <View style={{ transform: [{ scaleX: -1 }] }}>
          <Icon name="chevron" size={20} color={c.high} />
        </View>
      </Pressable>
      {children}
      <T role="heading" lines={1} style={{ flex: 1 }}>
        {title}
      </T>
      {right ? (
        <T role="label" tone="low">
          {right}
        </T>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: space.md, paddingTop: space.xs },
  collapsed: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: size.collapsedHeader,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: space.md,
    borderBottomWidth: 0.5,
    zIndex: 12,
    overflow: 'hidden',
  },
  board: {
    height: size.collapsedHeader,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.md,
    borderBottomWidth: 0.5,
    zIndex: 12,
    overflow: 'hidden',
  },
});
