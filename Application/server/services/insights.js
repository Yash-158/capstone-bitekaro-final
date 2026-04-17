require('dotenv').config();
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

async function generateInsights(analyticsData) {
  const {
    today_revenue,
    yesterday_revenue,
    today_orders,
    yesterday_orders,
    avg_order_value,
    top_items,
    low_stock_items,
    category_revenue,
    hourly_data
  } = analyticsData

  const prompt = `You are a smart business advisor for a cafe in Ahmedabad, India called BiteKaro. 
Analyze this today's sales data and give exactly 3 short, actionable insights in simple English.

Sales Data:
- Today's revenue: Rs.${today_revenue} (Yesterday: Rs.${yesterday_revenue})
- Orders today: ${today_orders} (Yesterday: ${yesterday_orders})
- Average order value: Rs.${avg_order_value}
- Top selling item: ${top_items?.[0]?.item_name || 'N/A'} with ${top_items?.[0]?.count || 0} orders
- Category breakdown: ${JSON.stringify(category_revenue)}
- Low stock items: ${low_stock_items?.map(i => i.name + ' (' + i.inventory_count + ' left)').join(', ') || 'None'}
- Busiest hour today: ${hourly_data?.sort((a,b) => b.orders - a.orders)?.[0]?.hour || 'N/A'}:00

Give exactly 3 insights. Each insight must:
- Start with an emoji (use ✅ for good news, ⚠️ for warnings, 💡 for opportunities)
- Be 1-2 sentences maximum
- Be specific with numbers from the data
- Be directly actionable for the cafe owner

Respond ONLY with a JSON array of 3 strings. No other text.
Example format: ["✅ insight one", "⚠️ insight two", "💡 insight three"]`

  try {
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.GROQ_API_KEY}`
      },
      body: JSON.stringify({
        model: 'llama3-70b-8192',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.4,
        max_tokens: 300
      })
    })

    const data = await response.json();
    let text = data.choices?.[0]?.message?.content?.trim();
    if (text) {
      text = text.replace(/```json/gi, '').replace(/```/g, '').trim();
    }
    
    // Parse JSON array from response
    const insights = JSON.parse(text);
    return Array.isArray(insights) ? insights : getFallbackInsights(analyticsData);
    
  } catch (error) {
    console.error('Groq API full error:', JSON.stringify(error));
    if (error.response) {
      const errText = await error.response.text();
      console.error('Groq response body:', errText);
    }
    return getFallbackInsights(analyticsData);
  }
}

function getFallbackInsights(data) {
  // Rule-based fallback if Groq is unavailable
  const insights = []
  
  const revChange = data.yesterday_revenue > 0 
    ? ((data.today_revenue - data.yesterday_revenue) / data.yesterday_revenue * 100).toFixed(1)
    : 0
  
  if (revChange > 0) {
    insights.push(`✅ Revenue is up ${revChange}% today (Rs.${data.today_revenue}) compared to yesterday. Great performance!`)
  } else {
    insights.push(`⚠️ Revenue is down ${Math.abs(revChange)}% today. Consider promoting your top items.`)
  }
  
  if (data.top_items?.[0]) {
    insights.push(`💡 ${data.top_items[0].item_name} is your bestseller with ${data.top_items[0].count} orders today.`)
  } else {
    insights.push(`💡 Keep track of your bestsellers to plan inventory better.`)
  }
  
  if (data.low_stock_items?.length > 0) {
    insights.push(`⚠️ Low stock alert: ${data.low_stock_items[0].name} has only ${data.low_stock_items[0].inventory_count} units left. Restock soon.`)
  } else {
    insights.push(`✅ All items are well-stocked. Excellent inventory management!`)
  }
  
  return insights
}

module.exports = { generateInsights }
