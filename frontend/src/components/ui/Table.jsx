import React from 'react';
import styles from './Table.module.css';

export function Table({ columns, rows, rowKey, onRowClick, expandedRows = {}, onToggleExpand, renderExpanded }) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.align === 'right' ? styles.num : ''}>
                {col.label}
              </th>
            ))}
            {onToggleExpand && <th className={styles.num} />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const key = rowKey ? row[rowKey] : idx;
            const expanded = !!expandedRows[key];
            return (
              <React.Fragment key={key}>
                <tr
                  className={`${styles.row} ${onRowClick ? styles.clickable : ''}`}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={col.align === 'right' ? styles.num : ''}>
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                  {onToggleExpand && (
                    <td className={styles.expandCell}>
                      <button
                        type="button"
                        className={styles.expandBtn}
                        onClick={(e) => { e.stopPropagation(); onToggleExpand(key); }}
                        aria-label={expanded ? '收起' : '展开'}
                      >
                        {expanded ? '\u2212' : '+'}
                      </button>
                    </td>
                  )}
                </tr>
                {expanded && renderExpanded && (
                  <tr>
                    <td colSpan={columns.length + 1} className={styles.expandedCell}>
                      {renderExpanded(row)}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
