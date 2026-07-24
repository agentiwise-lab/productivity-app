/**
 * One row shape, everywhere a list appears.
 *
 * The old list was text on a hairline, and that is the whole reason it read as
 * primitive: a rule between two rows separates them by exactly one pixel, so no
 * amount of good type stops the list looking like one undifferentiated block.
 * A row here is a discrete card with 8pt of air under it.
 *
 * Every row carries its category twice: a 3pt bar down the leading edge, and a
 * 120pt wash at 16% behind the mark. Two signals rather than one, so the row
 * survives being read at arm's length and survives greyscale.
 */

import React from 'react';
import { Pressable, View, type StyleProp, type ViewStyle } from 'react-native';
import { radius, size, space, useTheme, type Category } from '../theme';
import { Icon, type GlyphName } from './Icon';
import { T, Wash } from './ui';

export interface RowProps {
  /**
   * `null` where the row has no category at all, which is not the same as
   * "none". A connection in You is plumbing: painting a hue down its edge
   * promises a priority signal the row has no way to mean, and five settings
   * rows each wearing a coloured rule is the single clearest thing that made
   * that screen read as decorated rather than designed.
   */
  category: Category | null;
  /** The mark, a time, or an avatar. Whatever names the row's origin. */
  leading?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: string | null;
  /** Top right: an age, a duration, a count. Always machine-set. */
  meta?: string | null;
  /** Under the meta, smaller and quieter: a repo, an id, a channel. */
  submeta?: string | null;
  /** Right of the text, at heading size. A count that is the row's point. */
  value?: string | null;
  /** Only ever set where there is somewhere to go. */
  glyph?: GlyphName | null;
  trailing?: React.ReactNode;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

export function Row({
  category,
  leading,
  title,
  subtitle,
  meta,
  submeta,
  value,
  glyph,
  trailing,
  onPress,
  style,
}: RowProps) {
  const c = useTheme();

  const content = (
    <>
      {category ? (
        <>
          <Wash category={category} width={120} />
          <View
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: 3,
              backgroundColor: c.hue[category],
              zIndex: 2,
            }}
          />
        </>
      ) : null}
      {leading}
      {/* No gap. Body is 15/20 and secondary is 13/20, so the two line boxes
          already carry their own leading, and 20 + 20 + 24 of padding lands
          the row on exactly the 64 it is specified at. */}
      <View style={{ flex: 1, minWidth: 0 }}>
        {typeof title === 'string' ? (
          <T role="body" lines={1}>
            {title}
          </T>
        ) : (
          title
        )}
        {subtitle ? (
          <T role="secondary" tone="mid" lines={1}>
            {subtitle}
          </T>
        ) : null}
      </View>
      {value ? (
        // Secondary rather than heading, and the prose face rather than mono.
        // A board's value is often a phrase ("16 done · 13 left"), and set at
        // 17pt in Geist Mono it outweighed the project it belonged to and read
        // as terminal output.
        <T role="secondary" tone="mid" lines={1}>
          {value}
        </T>
      ) : null}
      {meta || submeta ? (
        <View style={{ alignItems: 'flex-end' }}>
          {meta ? (
            <T role="secondary" tone="mid" numeric>
              {meta}
            </T>
          ) : null}
          {submeta ? (
            // 11/16 rather than the secondary role's 13/20: this is the
            // quietest thing on the row and it must not compete with the age
            // directly above it.
            <T role="label" tone="low" numeric style={{ letterSpacing: 0 }}>
              {submeta}
            </T>
          ) : null}
        </View>
      ) : null}
      {glyph ? <Icon name={glyph} size={14} color={c.low} /> : null}
      {trailing}
    </>
  );

  const shape: StyleProp<ViewStyle> = [
    {
      flexDirection: 'row',
      alignItems: 'center',
      gap: space.sm,
      marginHorizontal: space.md,
      marginBottom: space.xs,
      padding: space.sm,
      backgroundColor: c.surface,
      borderRadius: radius.md,
      minHeight: size.row,
      overflow: 'hidden',
    },
    style,
  ];

  if (!onPress) return <View style={shape}>{content}</View>;
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [shape, pressed ? { opacity: 0.7 } : null]}
    >
      {content}
    </Pressable>
  );
}
