from mizani.formatters import *
from plotnine import *
import yfinance as yf
import pandas as pd
import numpy as np

ANNUAL_RATE = 0.07
MONTHLY_INVESTMENT = 100
MONTHLY_RATE = 1 + (ANNUAL_RATE / 12)
TODAY = pd.to_datetime('today').strftime("%Y-%m-%d")

# Get the SP500 historical price
sp500 = yf.download("SPY", "2000-01-01", end=TODAY, interval='1mo')["Close"].reset_index()
sp500["SP500 Return"] = (sp500["Close"] / sp500.loc[0, "Close"]) - 1

# Dollar Cost Average (DCA)
df_dca = sp500.copy(deep=True)

df_dca["Monthly Investment"] = MONTHLY_INVESTMENT
df_dca["Stocks to Buy"] = MONTHLY_INVESTMENT / df_dca["Close"]
df_dca["Total Investment"] = df_dca["Monthly Investment"].cumsum()
df_dca["Accumulated Stocks"] = df_dca["Stocks to Buy"].cumsum()
df_dca["Portfolio Value"] = df_dca["Accumulated Stocks"] * df_dca["Close"]
df_dca["Avg Buy Price DCA"] = df_dca["Total Investment"] / df_dca["Accumulated Stocks"]
df_dca["DCA Return"] = (df_dca["Portfolio Value"] / df_dca["Total Investment"]) - 1


# Value Average (VA)
df_va = sp500.copy(deep=True)
VALUE_INVESTMENT = MONTHLY_INVESTMENT
df_va.loc[0, "Target Portfolio Value"] = MONTHLY_INVESTMENT
df_va.loc[0, "Portfolio Value Before Buy"] = 0
df_va.loc[0, "Amount to Buy"] = MONTHLY_INVESTMENT
df_va.loc[0, "Stocks to Buy"] = df_va.loc[0, "Amount to Buy"] / df_va.loc[0, "Close"]
df_va.loc[0, "Accumulated Stocks"] = df_va.loc[0, "Stocks to Buy"]
df_va.loc[0, "Total Investment"] = MONTHLY_INVESTMENT
df_va.loc[0, "Avg Buy Price VA"] = np.nan
df_va.loc[0, "Avg Sell Price VA"] = np.nan
df_va.loc[0, "Liquidity"] = 0
df_va.loc[0, "VA Return"] = 0

for i in range(1, len(df_va)):
    VALUE_INVESTMENT = VALUE_INVESTMENT * (1 + ANNUAL_RATE / 12) + MONTHLY_INVESTMENT
    df_va.loc[i, "Target Portfolio Value"] = VALUE_INVESTMENT
    df_va.loc[i, "Portfolio Value Before Buy"] = df_va.loc[i - 1, "Accumulated Stocks"] * df_va.loc[i, "Close"]
    df_va.loc[i, "Amount to Buy"] = df_va.loc[i, "Target Portfolio Value"] - df_va.loc[i, "Portfolio Value Before Buy"]
    df_va.loc[i, "Stocks to Buy"] = df_va.loc[i, "Amount to Buy"] / df_va.loc[i, "Close"]
    df_va.loc[i, "Accumulated Stocks"] = df_va.loc[i - 1, "Accumulated Stocks"] + df_va.loc[i, "Stocks to Buy"]
    df_va.loc[i, "Total Investment"] = df_va.loc[i - 1, "Total Investment"] + df_va.loc[i, "Amount to Buy"]

    df_va.loc[i, "Avg Buy Price VA"] = (
            (df_va.iloc[:i]["Close"] * (df_va.iloc[:i]["Stocks to Buy"] * (df_va.iloc[:i]["Stocks to Buy"] > 0)))
            .sum() / df_va.iloc[:i].loc[df_va.iloc[:i]["Stocks to Buy"] > 0, "Stocks to Buy"].sum()
    )

    df_va.loc[i, "Avg Sell Price VA"] = (
            (df_va.iloc[:i]["Close"] * (df_va.iloc[:i]["Stocks to Buy"] * (df_va.iloc[:i]["Stocks to Buy"] < 0)))
            .sum() / df_va.iloc[:i].loc[df_va.iloc[:i]["Stocks to Buy"] < 0, "Stocks to Buy"].sum()
    )

    if df_va.loc[i, "Amount to Buy"] < 0:
        df_va.loc[i, "Liquidity"] = df_va.loc[i - 1, "Liquidity"] - df_va.loc[i, "Amount to Buy"]
    else:
        if df_va.loc[i, "Amount to Buy"] > df_va.loc[i - 1, "Liquidity"]:
            df_va.loc[i, "Liquidity"] = 0
        else:
            df_va.loc[i, "Liquidity"] = df_va.loc[i - 1, "Liquidity"] - df_va.loc[i, "Amount to Buy"]

df_va["VA Return"] = ((df_va["Target Portfolio Value"] + df_va["Liquidity"]) / (df_va["Total Investment"] + df_va["Liquidity"])) - 1
df_va.to_csv("VA.csv", sep=";", decimal=",")

# Merge dataframes
df = (df_dca[["Date", "SP500 Return", "Portfolio Value", "DCA Return", "Accumulated Stocks", "Avg Buy Price DCA"]]
      .merge(df_va[["Date", "Target Portfolio Value", "Portfolio Value Before Buy", "VA Return", "Accumulated Stocks", "Avg Buy Price VA", "Avg Sell Price VA"]],
             on="Date", how="inner", suffixes=(" DCA", " VA")))


# Plots
plot1 = (ggplot(df)
         + geom_line(aes(x="Date", y="Portfolio Value", color='"A"'), size=1)
         + geom_line(aes(x="Date", y="Target Portfolio Value", color='"B"'), size=1)
         + geom_line(aes(x="Date", y="Portfolio Value Before Buy", color='"C"'), size=1)

         + scale_x_date(date_breaks="1 year",
                        expand=(0, 0),
                        labels=date_format("%Y"),
                        limits=pd.to_datetime(["2000-01-01", TODAY]))

         + scale_y_continuous(expand=(0, 0),
                              breaks=range(0, 90_000 + 1, 10_000),
                              labels=dollar_format(digits=0),
                              limits=(0, 90_000))

         + scale_color_manual(values={"A": "#4472C4", "B": "#ED7D31", "C": "#A5A5A5"}, labels=[" DCA", " VA before Buy", " VA after Buy"])

         + labs(title="DCA vs VA: Portfolio Value",
                x="", y="",
                caption="Own elaboration. Source: S&P 500 (SPY) from Yahoo Finance. Created by @jaldeko.")
         + theme_minimal()
         + theme(
            plot_title=element_text(face="bold", hjust=0.5, size=16),
            plot_caption=element_text(size=8, face="italic"),
            panel_grid_major=element_line(linetype="solid", linewidth=0.5, color="#C0C0C0"),
            panel_grid_minor=element_blank(),
            axis_line=element_line(colour="#000000"),
            axis_ticks=element_line(colour="#000000"),
            axis_text=element_text(face="bold", color="#000000"),
            legend_title=element_blank(),
            legend_position="top",
            legend_box_just="left",
            legend_box="horizontal",
            legend_text=element_text(size=12, colour="#000000")
            )
         )

plot1.save(filename="DCA vs VA - Portfolio Value.jpg", format="jpg", width=1280/125, height=720/125, dpi=125)


plot2 = (ggplot(df)
         + geom_line(aes(x="Date", y="DCA Return", color='"A"'), size=1)
         + geom_line(aes(x="Date", y="SP500 Return", color='"B"'), size=1)
         + geom_line(aes(x="Date", y="VA Return", color='"C"'), size=1)

         + scale_x_date(date_breaks="1 year",
                        expand=(0, 0),
                        labels=date_format("%Y"),
                        limits=pd.to_datetime(["2000-01-01", TODAY]))

         + scale_y_continuous(expand=(0, 0),
                              breaks=np.arange(-0.5, 3 + 0.1, 0.5),
                              labels=percent_format(),
                              limits=(-0.5, 3))

         + scale_color_manual(values={"A": "#4472C4", "B": "#ED7D31", "C": "#A5A5A5"}, labels=[" DCA", " SP 500", " VA"])

         + labs(title="DCA vs VA: Portfolio Yield",
                x="", y="",
                caption="Own elaboration. Source: S&P 500 (SPY) from Yahoo Finance. Created by @jaldeko.")
         + theme_minimal()
         + theme(
            plot_title=element_text(face="bold", hjust=0.5, size=16),
            plot_caption=element_text(size=8, face="italic"),
            panel_grid_major=element_line(linetype="solid", linewidth=0.5, color="#C0C0C0"),
            panel_grid_minor=element_blank(),
            axis_line=element_line(colour="#000000"),
            axis_ticks=element_line(colour="#000000"),
            axis_text=element_text(face="bold", color="#000000"),
            legend_title=element_blank(),
            legend_position="top",
            legend_box_just="left",
            legend_box="horizontal",
            legend_text=element_text(size=12, colour="#000000")
            )
         )

plot2.save(filename="DCA vs VA - Yield.jpg", format="jpg", width=1280/125, height=720/125, dpi=125)


plot3 = (ggplot(df)
         + geom_line(aes(x="Date", y="Accumulated Stocks DCA", color='"DCA"'), size=1)
         + geom_line(aes(x="Date", y="Accumulated Stocks VA", color='"VA"'), size=1)

         + scale_x_date(date_breaks="1 year",
                        expand=(0, 0),
                        labels=date_format("%Y"),
                        limits=pd.to_datetime(["2000-01-01", TODAY]))

         + scale_y_continuous(expand=(0, 0),
                              breaks=range(0, 250 + 1, 50),
                              limits=(0, 250))

         + scale_color_manual(values={"DCA": "#4472C4", "VA": "#A5A5A5"}, labels=[" DCA", " VA"])

         + labs(title="DCA vs VA: Portfolio Stocks",
                x="", y="",
                caption="Own elaboration. Source: S&P 500 (SPY) from Yahoo Finance. Created by @jaldeko.")
         + theme_minimal()
         + theme(
            plot_title=element_text(face="bold", hjust=0.5, size=16),
            plot_caption=element_text(size=8, face="italic"),
            panel_grid_major=element_line(linetype="solid", linewidth=0.5, color="#C0C0C0"),
            panel_grid_minor=element_blank(),
            axis_line=element_line(colour="#000000"),
            axis_ticks=element_line(colour="#000000"),
            axis_text=element_text(face="bold", color="#000000"),
            legend_title=element_blank(),
            legend_position="top",
            legend_box_just="left",
            legend_box="horizontal",
            legend_text=element_text(size=12, colour="#000000")
            )
         )

plot3.save(filename="DCA vs VA - Portfolio Stocks.jpg", format="jpg", width=1280/125, height=720/125, dpi=125)


plot4 = (ggplot(df)
         + geom_line(aes(x="Date", y="Avg Buy Price DCA", color='"A"'), size=1)
         + geom_line(aes(x="Date", y="Avg Buy Price VA", color='"B"'), size=1)
         + geom_line(aes(x="Date", y="Avg Sell Price VA", color='"C"'), size=1)

         + scale_x_date(date_breaks="1 year",
                        expand=(0, 0),
                        labels=date_format("%Y"),
                        limits=pd.to_datetime(["2000-01-01", TODAY]))

         + scale_y_continuous(expand=(0, 0),
                              breaks=range(0, 300 + 1, 50),
                              labels=dollar_format(digits=0),
                              limits=(0, 300))

         + scale_color_manual(values={"A": "#4472C4", "B": "#ED7D31", "C": "#A5A5A5"}, labels=[" Avg Buy Price DCA", " Avg Buy Price VA", " Avg Sell Price VA"])

         + labs(title="DCA vs VA: Average Buy-Sell Price",
                x="", y="",
                caption="Own elaboration. Source: S&P 500 (SPY) from Yahoo Finance. Created by @jaldeko.")
         + theme_minimal()
         + theme(
            plot_title=element_text(face="bold", hjust=0.5, size=16),
            plot_caption=element_text(size=8, face="italic"),
            panel_grid_major=element_line(linetype="solid", linewidth=0.5, color="#C0C0C0"),
            panel_grid_minor=element_blank(),
            axis_line=element_line(colour="#000000"),
            axis_ticks=element_line(colour="#000000"),
            axis_text=element_text(face="bold", color="#000000"),
            legend_title=element_blank(),
            legend_position="top",
            legend_box_just="left",
            legend_box="horizontal",
            legend_text=element_text(size=12, colour="#000000")
            )
         )

plot4.save(filename="DCA vs VA - Average Buy-Sell Price.jpg", format="jpg", width=1280/125, height=720/125, dpi=125)
