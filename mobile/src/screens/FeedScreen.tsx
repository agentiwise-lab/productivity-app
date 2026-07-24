/**
 * The Feed: one thing at a time, filling the screen.
 *
 * Cards are grouped Urgent, By EOD, Can wait, then Later, and swiped
 * horizontally in that order. There are no divider cards between the groups,
 * no progress rail along the top, and no count on the tab: the card's own chip
 * already says which group it belongs to, and three more ways of saying it is
 * three more things to keep in agreement.
 *
 * The list scrolls with the finger at 1:1 and can be reversed mid-flight,
 * because a card that commits the moment you start moving is a card that acts
 * on a gesture you had not finished making.
 */

import React, { useMemo, useRef, useState } from "react";
import { FlatList, useWindowDimensions, View } from "react-native";
import { size, useTheme } from "../theme";
import { FeedCard } from "../components/FeedCard";
import { Clear, Skeleton } from "../components/states";
import type { FeedRow, Tier } from "../api/types";

const ORDER: Tier[] = ["urgent", "today", "can_wait", "noise"];

export function FeedScreen({
  rows,
  loading,
  onAction,
  onOpen,
}: {
  rows: FeedRow[];
  loading: boolean;
  onAction: (row: FeedRow, action: string) => void;
  onOpen: (row: FeedRow, compose?: boolean) => void;
}) {
  const c = useTheme();
  const { width, height: screen } = useWindowDimensions();
  const list = useRef<FlatList<FeedRow>>(null);
  // Seeded rather than started at zero. `onLayout` does not fire until after
  // the first paint, so a card mounted at height 0 drew one blank frame every
  // time the tab was entered: the screen went black, then the card appeared.
  // The seed is an estimate and the measurement immediately corrects it.
  const [height, setHeight] = useState(screen - size.tabBar);

  const ordered = useMemo(
    () =>
      [...rows]
        .filter((row) => row.status !== "acted" && row.status !== "dismissed")
        .sort(
          (a, b) =>
            ORDER.indexOf(a.tier) - ORDER.indexOf(b.tier) ||
            b.priority_score - a.priority_score,
        ),
    [rows],
  );

  if (loading && ordered.length === 0) {
    return (
      <View
        style={{ flex: 1, backgroundColor: c.canvas, justifyContent: "center" }}
      >
        <Skeleton rows={4} />
      </View>
    );
  }

  if (ordered.length === 0) {
    return (
      <View
        style={{ flex: 1, backgroundColor: c.canvas, justifyContent: "center" }}
      >
        <Clear heldBack={rows.length - ordered.length} />
      </View>
    );
  }

  return (
    // The card's height is measured rather than inherited. A percentage on a
    // horizontal list's item resolves against a content container that is
    // itself auto-height, so the card collapsed to its text: the bloom ended
    // up above the fold and the rail floated over the middle of the copy.
    <View
      style={{ flex: 1, backgroundColor: c.canvas }}
      onLayout={(event) => setHeight(event.nativeEvent.layout.height)}
    >
      <FlatList
        ref={list}
        data={ordered}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(row) => row.id}
        style={{ flex: 1 }}
        // Every card is exactly one screen wide, so the list never has to measure
        // anything to know where a page starts.
        getItemLayout={(_, index) => ({
          length: width,
          offset: width * index,
          index,
        })}
        renderItem={({ item }) => (
          <View style={{ width, height }}>
            <FeedCard row={item} onAction={onAction} onOpen={onOpen} />
          </View>
        )}
      />
    </View>
  );
}
