// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"context"
	"fmt"
	"net/url"
	"time"

	"github.com/go-logr/logr"
	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/silogen/agent/internal/config"
)

// MessageHandler processes a message. Return error to requeue.
type MessageHandler func(ctx context.Context, msg *RawMessage) error

// Consumer consumes messages from RabbitMQ.
type Consumer struct {
	amqpURL   string
	queueName string
	handler   MessageHandler
	logger    logr.Logger
	conn      *amqp.Connection
	channel   *amqp.Channel
}

// NewConsumer creates a consumer.
func NewConsumer(rabbitMqConfig config.RabbitMQConfig, handler MessageHandler, logger logr.Logger) *Consumer {
	encodedVHost := url.PathEscape(rabbitMqConfig.VHost)
	amqpURL := fmt.Sprintf("amqp://%s:%s@%s:%d/%s", rabbitMqConfig.User, rabbitMqConfig.Password, rabbitMqConfig.Host, rabbitMqConfig.Port, encodedVHost)

	return &Consumer{
		amqpURL:   amqpURL,
		queueName: rabbitMqConfig.Queue,
		handler:   handler,
		logger:    logger,
	}
}

// Start connects and consumes until context is canceled.
func (c *Consumer) Start(ctx context.Context) error {
	for {
		if err := ctx.Err(); err != nil {
			return err
		}

		if err := c.connectAndConsume(ctx); err != nil {
			c.logger.Error(err, "consumer error")
			c.close()
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(5 * time.Second):
			}
		}
	}
}

func (c *Consumer) connectAndConsume(ctx context.Context) error {
	conn, err := amqp.Dial(c.amqpURL)
	if err != nil {
		return fmt.Errorf("connect failed: %w", err)
	}
	c.conn = conn

	ch, err := conn.Channel()
	if err != nil {
		return fmt.Errorf("channel failed: %w", err)
	}
	c.channel = ch

	qos := DefaultQoSConfig()
	if qosErr := ch.Qos(qos.PrefetchCount, qos.PrefetchSize, qos.Global); qosErr != nil {
		return fmt.Errorf("qos failed: %w", qosErr)
	}

	consumerCfg := DefaultConsumerConfig()
	deliveries, err := ch.Consume(
		c.queueName,
		consumerCfg.ConsumerTag,
		consumerCfg.AutoAck,
		consumerCfg.Exclusive,
		consumerCfg.NoLocal,
		consumerCfg.NoWait,
		consumerCfg.Args,
	)
	if err != nil {
		return fmt.Errorf("consume failed: %w", err)
	}

	c.logger.Info("consuming", "queue", c.queueName)

	connClosed := conn.NotifyClose(make(chan *amqp.Error, 1))

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case err := <-connClosed:
			return fmt.Errorf("connection closed: %v", err)
		case d, ok := <-deliveries:
			if !ok {
				return fmt.Errorf("channel closed")
			}
			c.handle(ctx, d)
		}
	}
}

func (c *Consumer) handle(ctx context.Context, d amqp.Delivery) {
	msg, err := ParseMessageEnvelope(d.Body)
	if err != nil {
		c.logger.Error(err, "parse failed")
		if nackErr := d.Nack(false, false); nackErr != nil {
			c.logger.Error(nackErr, "nack failed")
		}
		return
	}

	if err := c.handler(ctx, msg); err != nil {
		c.logger.Error(err, "handler failed", "type", msg.Type)
		if nackErr := d.Nack(false, true); nackErr != nil {
			c.logger.Error(nackErr, "nack failed")
		}
		return
	}

	if ackErr := d.Ack(false); ackErr != nil {
		c.logger.Error(ackErr, "ack failed")
	}
}

func (c *Consumer) close() {
	if c.channel != nil {
		c.channel.Close()
	}
	if c.conn != nil {
		c.conn.Close()
	}
}

// Close shuts down the consumer.
func (c *Consumer) Close() {
	c.close()
}
