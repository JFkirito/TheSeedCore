# -*- coding: utf-8 -*-
"""
TheSeedCore KafkaService Module

This module provides a service for managing Kafka producers, consumers, and administrative tasks within TheSeedCore ecosystem.
It includes functionalities for creating and managing Kafka clusters, producers, consumers, and topics, as well as sending and receiving messages.

Classes:
    - KafkaService:
        Singleton class that provides methods for managing Kafka clusters. It includes functionalities for adding clusters, creating producers and consumers, managing topics, and handling messages.

Features:
    - Cluster Management: Add and update Kafka clusters with specified configurations.
    - Producer and Consumer Management: Create and manage Kafka producers and consumers within specified clusters. Handle message sending and receiving.
    - Topic Management: Create and manage Kafka topics, including altering topic configurations and listing available topics.
    - Offset Management: Get and set offsets for Kafka topics and partitions.
    - Health Check: Monitor and check the health of Kafka clusters.
    - Logging: Comprehensive logging for all operations, aiding in monitoring and debugging.

This module is designed to provide robust Kafka integration within TheSeedCore, enabling efficient messaging and data streaming capabilities.
"""

from __future__ import annotations

import logging
import pickle
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient, TopicPartition
from kafka.admin import NewTopic, ConfigResource, ConfigResourceType

if TYPE_CHECKING:
    from .LoggerModule import TheSeedCoreLogger


class KafkaService:
    _INSTANCE: KafkaService = None
    _INITIALIZED: bool = False

    def __new__(cls, Logger: Union[TheSeedCoreLogger, logging.Logger], *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(KafkaService).__new__(cls)
        return cls._INSTANCE

    def __init__(self, Logger: logging.Logger):
        if not self._INITIALIZED:
            self._Logger = Logger
            self._Clusters: Dict[str, Dict[str, Any]] = {}
            KafkaService._INITIALIZED = True

    def addCluster(self, cluster_id: str, admin_configs: Optional[Dict[str, Any]] = None):
        if cluster_id not in self._Clusters:
            self._Clusters[cluster_id] = {
                "producers": {},
                "consumers": {},
                "admin_client": KafkaAdminClient(**admin_configs) if admin_configs else None
            }
            self._Logger.info(f"Cluster {cluster_id} added.")

    def updateClusterConfig(self, cluster_id: str, new_admin_configs: Dict[str, Any]):
        """更新集群配置"""
        if cluster_id in self._Clusters:
            try:
                self._Clusters[cluster_id]["admin_client"].close()
                self._Clusters[cluster_id]["admin_client"] = KafkaAdminClient(**new_admin_configs)
                self._Logger.info(f"Cluster {cluster_id} configuration updated.")
            except Exception as e:
                self._Logger.error(f"Updating cluster {cluster_id} configuration failed: {e}\n\n{traceback.format_exc()}")
        else:
            self._Logger.error(f"Update cluster config failed: Cluster {cluster_id} not found.")

    def monitorCluster(self, cluster_id: str):
        """监控集群状态"""
        if cluster_id in self._Clusters:
            try:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    metrics = admin_client.metrics()
                    self._Logger.info(f"Cluster {cluster_id} metrics: {metrics}")
                    return metrics
                else:
                    self._Logger.error(f"Monitor cluster failed: No admin client found for cluster {cluster_id}.")
            except Exception as e:
                self._Logger.error(f"Error during monitoring cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
        else:
            self._Logger.error(f"Monitor cluster failed: Cluster {cluster_id} not found.")
        return None

    def createProducer(self, cluster_id: str, client_id: str, **configs):
        if cluster_id in self._Clusters:
            configs["client_id"] = client_id
            producer = KafkaProducer(**configs)
            self._Clusters[cluster_id]["producers"][client_id] = producer
            self._Logger.info(f"Producer created for client_id: {client_id} in cluster {cluster_id}")
        else:
            self._Logger.error(f"Create producer failed: Cluster {cluster_id} not found.")

    def createConsumer(self, cluster_id: str, client_id: str, topics: List[str], **configs):
        if cluster_id in self._Clusters:
            configs["client_id"] = client_id
            consumer = KafkaConsumer(*topics, **configs)
            self._Clusters[cluster_id]["consumers"][client_id] = consumer
            self._Logger.info(f"Consumer created for client_id: {client_id} in cluster {cluster_id}")
        else:
            self._Logger.error(f"Create consumer failed: Cluster {cluster_id} not found.")

    def createTopic(self, cluster_id: str, topic_name: str, num_partitions: int, replication_factor: int, **configs):
        if cluster_id in self._Clusters:
            admin_client = self._Clusters[cluster_id]["admin_client"]
            if admin_client:
                try:
                    topic = NewTopic(name=topic_name, num_partitions=num_partitions, replication_factor=replication_factor, **configs)
                    admin_client.create_topics([topic])
                    self._Logger.debug(f"Topic {topic_name} created in cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Creating topic {topic_name} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Create topic failed: No admin client found for cluster {cluster_id}.")
        else:
            self._Logger.error(f"Create topic failed: Cluster {cluster_id} not found.")

    def sendMessage(self, cluster_id: str, client_id: str, topic: str, data: Any):
        if cluster_id in self._Clusters:
            producer = self._Clusters[cluster_id]["producers"].get(client_id)
            if producer:
                serialized_data = pickle.dumps(data)
                producer.send(topic, value=serialized_data).add_callback(self.onSendSuccess).add_errback(self.onSendError)
                self._Logger.info(f"Message sent to topic {topic} by producer {client_id} in cluster {cluster_id}")
            else:
                self._Logger.error(f"Send message failed: Producer with client_id {client_id} not found in cluster {cluster_id}.")
        else:
            self._Logger.error(f"Send message failed: Cluster {cluster_id} not found.")

    def receiveMessage(self, cluster_id: str, client_id: str, msg_callback):
        if cluster_id in self._Clusters:
            consumer = self._Clusters[cluster_id]["consumers"].get(client_id)
            if consumer:
                for msg in consumer:
                    data = pickle.loads(msg.value)
                    msg_callback(data)
                self._Logger.info(f"Messages received by consumer {client_id} in cluster {cluster_id}")
            else:
                self._Logger.error(f"Receive message failed: Consumer with client_id {client_id} not found in cluster {cluster_id}.")
        else:
            self._Logger.error(f"Receive message failed: Cluster {cluster_id} not found.")

    def onSendSuccess(self, record_metadata):
        self._Logger.info(f"Message sent successfully: {record_metadata.topic} - {record_metadata.partition} - {record_metadata.offset}")

    def onSendError(self, exception):
        self._Logger.error(f"Error sending message: {exception}")

    def closeSingleProducer(self, cluster_id: str, client_id: str):
        if cluster_id in self._Clusters:
            producer = self._Clusters[cluster_id]["producers"].get(client_id)
            if producer:
                try:
                    producer.close()
                    del self._Clusters[cluster_id]["producers"][client_id]
                    self._Logger.info(f"Producer {client_id} closed and removed from cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Close producer {client_id} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Close producer failed: Producer with client_id {client_id} not found in cluster {cluster_id}.")
        else:
            self._Logger.error(f"Close producer failed: Cluster {cluster_id} not found.")

    def closeSingleConsumer(self, cluster_id: str, client_id: str):
        if cluster_id in self._Clusters:
            consumer = self._Clusters[cluster_id]["consumers"].get(client_id)
            if consumer:
                try:
                    consumer.close()
                    del self._Clusters[cluster_id]["consumers"][client_id]
                    self._Logger.info(f"Consumer {client_id} closed and removed from cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Close consumer {client_id} in cluster {cluster_id} failed: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Close consumer failed: Consumer with client_id {client_id} not found in cluster {cluster_id}.")
        else:
            self._Logger.error(f"Close consumer failed: Cluster {cluster_id} not found.")

    def closeAllProducers(self, cluster_id: str):
        if cluster_id in self._Clusters:
            for client_id in list(self._Clusters[cluster_id]["producers"].keys()):
                self.closeSingleProducer(cluster_id, client_id)
        else:
            self._Logger.error(f"Close all producers failed: Cluster {cluster_id} not found.")

    def closeAllConsumers(self, cluster_id: str):
        if cluster_id in self._Clusters:
            for client_id in list(self._Clusters[cluster_id]["consumers"].keys()):
                self.closeSingleConsumer(cluster_id, client_id)
        else:
            self._Logger.error(f"Close all consumers failed: Cluster {cluster_id} not found.")

    def getProducer(self, cluster_id: str, client_id: str):
        if cluster_id in self._Clusters:
            try:
                return self._Clusters[cluster_id]["producers"][client_id]
            except KeyError:
                raise ValueError(f"Producer with client_id {client_id} not found in cluster {cluster_id}.")
        else:
            raise ValueError(f"Cluster {cluster_id} not found.")

    def getConsumer(self, cluster_id: str, client_id: str):
        if cluster_id in self._Clusters:
            try:
                return self._Clusters[cluster_id]["consumers"][client_id]
            except KeyError:
                raise ValueError(f"Consumer with client_id {client_id} not found in cluster {cluster_id}.")
        else:
            raise ValueError(f"Cluster {cluster_id} not found.")

    def listTopics(self, cluster_id: str):
        if cluster_id in self._Clusters:
            admin_client = self._Clusters[cluster_id]["admin_client"]
            if admin_client:
                try:
                    topics = admin_client.list_topics()
                    self._Logger.info(f"Available topics in cluster {cluster_id}: {topics}")
                    return topics
                except Exception as e:
                    self._Logger.error(f"Error listing topics in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"List topics failed: No admin client found for cluster {cluster_id}.")
        else:
            self._Logger.error(f"List topics failed: Cluster {cluster_id} not found.")
        return []

    def listConsumerGroups(self, cluster_id: str):
        if cluster_id in self._Clusters:
            admin_client = self._Clusters[cluster_id]["admin_client"]
            if admin_client:
                try:
                    consumer_groups = admin_client.list_consumer_groups()
                    self._Logger.info(f"Consumer groups in cluster {cluster_id}: {consumer_groups}")
                    return consumer_groups
                except Exception as e:
                    self._Logger.error(f"Error listing consumer groups in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"List consumer groups failed: No admin client found for cluster {cluster_id}.")
        else:
            self._Logger.error(f"List consumer groups failed: Cluster {cluster_id} not found.")
        return []

    def describeConsumerGroup(self, cluster_id: str, group_id: str):
        if cluster_id in self._Clusters:
            admin_client = self._Clusters[cluster_id]["admin_client"]
            if admin_client:
                try:
                    group_description = admin_client.describe_consumer_groups([group_id])
                    self._Logger.info(f"Description for group {group_id} in cluster {cluster_id}: {group_description}")
                    return group_description
                except Exception as e:
                    self._Logger.error(f"Error describing consumer group {group_id} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Describe consumer group failed: No admin client found for cluster {cluster_id}.")
        else:
            self._Logger.error(f"Describe consumer group failed: Cluster {cluster_id} not found.")
        return {}

    def alterTopicConfig(self, cluster_id: str, topic_name: str, config: Dict[str, str]):
        if cluster_id in self._Clusters:
            admin_client = self._Clusters[cluster_id]["admin_client"]
            if admin_client:
                try:
                    config_resource = ConfigResource(ConfigResourceType.TOPIC, topic_name)
                    config_entries = {k: v for k, v in config.items()}
                    admin_client.alter_configs({config_resource: config_entries})
                    self._Logger.info(f"Config for topic {topic_name} updated in cluster {cluster_id}.")
                except Exception as e:
                    self._Logger.error(f"Error altering topic config for {topic_name} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
            else:
                self._Logger.error(f"Alter topic config failed: No admin client found for cluster {cluster_id}.")
        else:
            self._Logger.error(f"Alter topic config failed: Cluster {cluster_id} not found.")

    def getOffsets(self, cluster_id: str, topic_name: str, partition: int):
        if cluster_id in self._Clusters:
            try:
                consumer = self._Clusters[cluster_id]["consumers"].get("offsets_consumer")
                if not consumer:
                    consumer = KafkaConsumer(group_id='offsets_consumer', enable_auto_commit=False)
                    self._Clusters[cluster_id]["consumers"]['offsets_consumer'] = consumer
                tp = TopicPartition(topic_name, partition)
                offsets = consumer.end_offsets([tp])
                self._Logger.info(f"Offsets for {topic_name} partition {partition} in cluster {cluster_id}: {offsets[tp]}")
                return offsets[tp]
            except Exception as e:
                self._Logger.error(f"Error getting offsets for {topic_name} partition {partition} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
        else:
            self._Logger.error(f"Get offsets failed: Cluster {cluster_id} not found.")
        return None

    def setOffsets(self, cluster_id: str, topic_name: str, partition: int, offset: int):
        if cluster_id in self._Clusters:
            try:
                consumer = self._Clusters[cluster_id]["consumers"].get("offsets_consumer")
                if not consumer:
                    consumer = KafkaConsumer(group_id='offsets_consumer', enable_auto_commit=False)
                    self._Clusters[cluster_id]["consumers"]['offsets_consumer'] = consumer
                tp = TopicPartition(topic_name, partition)
                consumer.seek(tp, offset)
                self._Logger.info(f"Offset for {topic_name} partition {partition} set to {offset} in cluster {cluster_id}")
            except Exception as e:
                self._Logger.error(f"Error setting offsets for {topic_name} partition {partition} in cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
        else:
            self._Logger.error(f"Set offsets failed: Cluster {cluster_id} not found.")

    def checkHealth(self, cluster_id: str):
        if cluster_id in self._Clusters:
            try:
                admin_client = self._Clusters[cluster_id]["admin_client"]
                if admin_client:
                    brokers = admin_client.describe_cluster().brokers
                    if brokers:
                        self._Logger.info(f"Cluster {cluster_id} health check passed. Brokers: {brokers}")
                        return True
                    else:
                        self._Logger.warning(f"No brokers found in the cluster {cluster_id}.")
                else:
                    self._Logger.error(f"Check health failed: No admin client found for cluster {cluster_id}.")
            except Exception as e:
                self._Logger.error(f"Error during health check for cluster {cluster_id}: {e}\n\n{traceback.format_exc()}")
        else:
            self._Logger.error(f"Check health failed: Cluster {cluster_id} not found.")
        return False
