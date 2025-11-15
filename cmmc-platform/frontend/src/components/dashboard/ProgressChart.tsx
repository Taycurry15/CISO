import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { ProgressOverTimeData } from '@/types';

export interface ProgressChartProps {
  data: ProgressOverTimeData[];
  xKey?: string;
  yKey?: string;
  title?: string;
}

export const ProgressChart: React.FC<ProgressChartProps> = ({
  data,
  xKey = 'date',
  yKey = 'complianceRate',
  title,
}) => {
  const formattedData = data.map((item) => ({
    ...item,
    date: new Date(item.date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
  }));

  return (
    <div>
      {title && <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey={xKey}
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            domain={[0, 100]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke="#0284c7"
            strokeWidth={2}
            dot={{ fill: '#0284c7', r: 4 }}
            activeDot={{ r: 6 }}
            name="Compliance Rate (%)"
          />
          <Line
            type="monotone"
            dataKey="metControls"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ fill: '#22c55e', r: 4 }}
            name="Met Controls"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
