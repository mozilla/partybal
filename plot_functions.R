integer_breaks <- function(x) {
    if(x[2] - x[1] <= 6) {
        seq(ceiling(x[1]), floor(x[2]), by = 1)
    } else {
        pretty(x, n=6)
    }
}

index_label <- function(x) {
    list(daily="Day", weekly="Week")[[x]]
}

labels_for <- function(period) {
    inner <- function(s) {
        paste(index_label(period), s)
    }
    as_labeller(inner)
}

plot_deciles <- function(df, metric, comparison, period) {
    df <- filter(df, metric == !!metric, statistic == "deciles")
    if(comparison == "none") {
        df <- filter(df, is.na(comparison))
        g <- ggplot(df, aes(parameter, point, ymin=lower, ymax=upper, group=branch)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            labs(title=metric, x="Quantile") +
            facet_wrap(~window_index, labeller=labels_for(period))
    } else {
        df <- filter(df, comparison == !!comparison)
        g <- ggplot(df, aes(parameter, point, ymin=lower, ymax=upper, group=0)) +
            geom_line(aes(color=branch)) +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            geom_hline(yintercept=0, alpha=0.6) +
            labs(title=paste0(metric, " (", comparison, ")"), x="Quantile") +
            facet_wrap(~window_index, labeller=labels_for(period))
        if(comparison == "relative_uplift") {
            g <- g + scale_y_continuous(labels=scales::percent)
        }
    }
    g
}

plot_mean <- function(df, metric, comparison, period, statistic="mean") {
    df <- filter(df, metric == !!metric, statistic == !!statistic)

    point_repr <- if(length(unique(df$window_index)) == 1) {
            list(
                geom_point(aes(color=branch), position=position_dodge(width=0.05)),
                geom_errorbar(aes(color=branch), position=position_dodge(width=0.05), width=0.03),
                scale_x_continuous(breaks=integer_breaks, limits=c(0.6, 1.4))
            )
        } else {
            list(
                geom_line(aes(color=branch)),
                scale_x_continuous(breaks=integer_breaks)
            )
        }

    if(comparison == "none") {
        df <- filter(df, is.na(comparison))
        g <- ggplot(df, aes(window_index, point, ymin=lower, ymax=upper, group=branch)) +
            point_repr +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            labs(title=metric, x=index_label(period))
    } else {
        df <- filter(df, comparison == !!comparison)
        g <- ggplot(df, aes(window_index, point, ymin=lower, ymax=upper, group=0)) +
            point_repr +
            geom_ribbon(aes(fill=branch), alpha=0.3) +
            labs(title=paste0(metric, " (", comparison, ")"), x=index_label(period)) +
            geom_blank(aes(ymin=-upper, ymax=-lower)) +
            geom_hline(yintercept=0, alpha=0.6)
        if(comparison == "relative_uplift") {
            g <- g + scale_y_continuous(labels=scales::percent)
        }
    }
    g
}

plot_binomial <- function(...) { plot_mean(..., "binomial") }

plot_count <- function(df, metric, comparison, period) {
    filter(df, metric == !!metric) %>%
        slice_min(window_index, n=1, with_ties=TRUE) %>%
        select(Branch=branch, Clients=point)
 }
