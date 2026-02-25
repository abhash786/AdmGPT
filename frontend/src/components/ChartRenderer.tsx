import React from 'react';
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    Cell
} from 'recharts';

interface ChartData {
    type: 'bar' | 'line' | 'pie';
    title: string;
    data: any[];
    xKey: string;
    yKeys: string[];
    colors?: string[];
}

interface ChartRendererProps {
    content: string;
}

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', '#00C49F', '#FFBB28', '#FF8042'];

// Error Boundary to prevent chart crashes from taking down the entire app
class ChartErrorBoundary extends React.Component<
    { children: React.ReactNode },
    { hasError: boolean; error?: Error }
> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error) {
        return { hasError: true, error };
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-sm">
                    <strong>Chart rendering error.</strong> The chart data was received but could not be displayed.
                </div>
            );
        }
        return this.props.children;
    }
}

const ChartRenderer: React.FC<ChartRendererProps> = React.memo(({ content }) => {
    let chartData: ChartData;

    try {
        chartData = JSON.parse(content);
    } catch (e) {
        // During streaming, content may be incomplete JSON — show a loading state
        const trimmed = content.trim();
        if (!trimmed || !trimmed.endsWith('}')) {
            // Likely still streaming — show placeholder
            return (
                <div className="my-4 p-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 shadow-sm">
                    <div className="flex items-center gap-2 text-gray-400">
                        <div className="w-4 h-4 border-2 border-gray-300 border-t-accent-500 rounded-full animate-spin" />
                        <span className="text-sm">Generating chart…</span>
                    </div>
                </div>
            );
        }
        // Content looks complete but is invalid JSON — show error
        return <div className="text-red-500 p-4 border border-red-200 rounded-xl">Error parsing chart data: Invalid JSON</div>;
    }

    const { type, title, data, xKey, yKeys, colors = COLORS } = chartData;

    // Use fixed dimensions to avoid ResponsiveContainer's resize-observer
    // infinite-loop bug with React 19 + recharts 3.x
    const WIDTH = 600;
    const HEIGHT = 300;

    const renderChart = () => {
        switch (type) {
            case 'bar':
                return (
                    <BarChart width={WIDTH} height={HEIGHT} data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey={xKey} />
                        <YAxis />
                        <Tooltip contentStyle={{ backgroundColor: '#1e1e2e', color: '#f5f5f5', border: '1px solid #3f3f5f', borderRadius: '8px', fontSize: '13px' }} itemStyle={{ color: '#e0e0e0' }} labelStyle={{ color: '#ffffff', fontWeight: 600 }} />
                        <Legend />
                        {yKeys.map((key, index) => (
                            <Bar key={key} dataKey={key} fill={colors[index % colors.length]} />
                        ))}
                    </BarChart>
                );
            case 'line':
                return (
                    <LineChart width={WIDTH} height={HEIGHT} data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey={xKey} />
                        <YAxis />
                        <Tooltip contentStyle={{ backgroundColor: '#1e1e2e', color: '#f5f5f5', border: '1px solid #3f3f5f', borderRadius: '8px', fontSize: '13px' }} itemStyle={{ color: '#e0e0e0' }} labelStyle={{ color: '#ffffff', fontWeight: 600 }} />
                        <Legend />
                        {yKeys.map((key, index) => (
                            <Line type="monotone" key={key} dataKey={key} stroke={colors[index % colors.length]} strokeWidth={2} />
                        ))}
                    </LineChart>
                );
            case 'pie':
                return (
                    <PieChart width={WIDTH} height={HEIGHT}>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey={yKeys[0]}
                            nameKey={xKey}
                        >
                            {data.map((_entry, index) => (
                                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                            ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: '#1e1e2e', color: '#f5f5f5', border: '1px solid #3f3f5f', borderRadius: '8px', fontSize: '13px' }} itemStyle={{ color: '#e0e0e0' }} labelStyle={{ color: '#ffffff', fontWeight: 600 }} />
                        <Legend />
                    </PieChart>
                );
            default:
                return <div>Unsupported chart type: {type}</div>;
        }
    };

    return (
        <ChartErrorBoundary>
            <div className="my-4 p-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 shadow-sm overflow-x-auto">
                {title && <h3 className="text-lg font-semibold mb-4 text-center text-gray-800 dark:text-gray-200">{title}</h3>}
                <div className="flex justify-center">
                    {renderChart()}
                </div>
            </div>
        </ChartErrorBoundary>
    );
});

ChartRenderer.displayName = 'ChartRenderer';

export default ChartRenderer;
