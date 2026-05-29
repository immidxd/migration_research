import React from "react";
import { Drawer } from "antd";

import { FlowsList } from "./FlowsList";

/** Flows now live in a dedicated drawer instead of cluttering the sidebar.
 *  Opened from the "Потоки (N)" button; the list inside stays scope-filtered
 *  and supports edit (✎) / delete per row. */
export const FlowsDrawer: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => (
  <Drawer
    title="Введені потоки"
    placement="left"
    open={open}
    onClose={onClose}
    width={400}
    styles={{ body: { padding: 0 } }}
  >
    <FlowsList />
  </Drawer>
);
