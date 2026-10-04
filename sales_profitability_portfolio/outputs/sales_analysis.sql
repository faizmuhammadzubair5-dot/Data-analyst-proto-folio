SELECT analysis_location, COUNT(*) AS line_items,
       ROUND(SUM(profit), 2) AS total_profit,
       ROUND(AVG(discount), 4) AS average_discount
FROM sales
GROUP BY analysis_location
ORDER BY total_profit DESC;

SELECT analysis_product, COUNT(*) AS line_items,
       ROUND(SUM(profit), 2) AS total_profit,
       ROUND(AVG(discount), 4) AS average_discount
FROM sales
GROUP BY analysis_product
ORDER BY total_profit DESC;
