#include <iostream>

extern "C" {
    void calculate_portfolio_ma_strategy(
        double* prices, double* dividends, double* weights,
        int num_assets, int length, double base_monthly_amount,
        int ma_window, bool reinvest,
        double* out_total_cost, double* out_final_value, double* out_total_dividends,
        double* out_history_assets, double* out_history_cost
    ) {
        double total_invested = 0.0;
        double total_dividends_received = 0.0;
        double cash_pocket = 0.0;
        double* shares = new double[num_assets]();

        for (int m = 0; m < length; m++) {
            for (int a = 0; a < num_assets; a++) {
                int current_idx = a * length + m;
                double current_price = prices[current_idx];
                double ma = 0.0;
                int count = 0;
                for (int i = 0; i < ma_window && (m - i) >= 0; i++) {
                    ma += prices[a * length + (m - i)];
                    count++;
                }
                ma /= count;
                double multiplier = (current_price < ma) ? 2.0 : 1.0;
                double actual_invest = base_monthly_amount * weights[a] * multiplier;
                total_invested += actual_invest;
                shares[a] += (actual_invest / current_price);
                double div_per_share = dividends[current_idx];
                if (div_per_share > 0) {
                    double current_div = shares[a] * div_per_share;
                    total_dividends_received += current_div;
                    
                    if (reinvest) {
                        shares[a] += (current_div / current_price);
                    } else {
                        cash_pocket += current_div;
                    }
                }
            }
            double current_month_value = cash_pocket;
            for (int a = 0; a < num_assets; a++) {
                current_month_value += shares[a] * prices[a * length + m];
            }
            out_history_assets[m] = current_month_value;
            out_history_cost[m] = total_invested;
        }
        *out_total_cost = total_invested;
        *out_final_value = out_history_assets[length - 1]; // 最後一月的價值就是最終價值
        *out_total_dividends = total_dividends_received;

        delete[] shares; 
    }
}